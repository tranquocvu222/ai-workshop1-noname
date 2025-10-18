#!/usr/bin/env python3
import os
import sys
import time
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
import json
import threading

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.box import ROUNDED
from dotenv import load_dotenv

# Import gTTS for Text-to-Speech
try:
    from gtts import gTTS
    from playsound import playsound
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("⚠️ Text-to-speech not available. Install with: pip install gTTS playsound")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.scheduler import Scheduler
from src.ai.azure_client import AzureOpenAIClient
try:
    from src.ai.vector_db import LocalChromaDB
except ImportError:
    LocalChromaDB = None

# Initialize Typer app
app = typer.Typer()
console = Console()

# Initialize scheduler and AI client
scheduler = Scheduler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/appointments.json"))
ai_client = AzureOpenAIClient()

# Store conversation history
conversation_history = []

# Current booking process info
current_booking = {
    "in_progress": False,
    "department": "",
    "department_code": "",
    "doctor": "",
    "date": "",
    "time": "",
    "patient": "",
    "symptoms": "",
    "notes": ""
}

# UI Styles
COMMAND_STYLE = "bold green"
HEADER_STYLE = "bold blue"
SUCCESS_STYLE = "bold green"
ERROR_STYLE = "bold red"
WARN_STYLE = "bold yellow"
INFO_STYLE = "cyan"
HIGHLIGHT_STYLE = "bold magenta"

# === TEXT TO SPEECH USING GTTS ===
def speak_text(text: str, non_blocking: bool = True):
    """
    Chuyển văn bản tiếng Việt sang giọng nói bằng gTTS (Google Text-to-Speech).
    Args:
        text: nội dung cần đọc
        non_blocking: nếu True, chạy ở thread riêng để không block UI
    """
    if not TTS_AVAILABLE or not text.strip():
        return

    # Làm sạch văn bản khỏi markdown, link, ký tự đặc biệt
    clean_text = re.sub(r'\[.*?\]', '', text)
    clean_text = re.sub(r'http\S+', '', clean_text)
    clean_text = re.sub(r'\*\*?(.*?)\*\*?', r'\1', clean_text)
    clean_text = re.sub(r'`(.*?)`', r'\1', clean_text)

    # Giới hạn độ dài tránh lỗi tạm thời
    if len(clean_text) > 500:
        truncated = clean_text[:500]
        last_period = truncated.rfind('.')
        if last_period > 0:
            clean_text = truncated[:last_period+1]
        else:
            clean_text = truncated

    def speak_thread():
        try:
            tts = gTTS(text=clean_text, lang='vi')
            filename = "temp_tts_output.mp3"
            tts.save(filename)
            playsound(filename)
            os.remove(filename)
        except Exception as e:
            console.print(f"[dim]⚠️ Lỗi khi đọc văn bản: {e}[/dim]")

    if non_blocking:
        threading.Thread(target=speak_thread, daemon=True).start()
    else:
        speak_thread()

# === VECTOR DB HELPERS ===
def get_relevant_faqs(query: str, max_results: int = 3) -> str:
    if not hasattr(ai_client, 'vdb') or not ai_client.vdb:
        return ""
    try:
        results = ai_client.vdb.query("faqs", query, n_results=max_results)
        if not results:
            return ""
        formatted_results = "Thông tin tham khảo từ FAQs:\n\n"
        for result in results:
            metadata = result.get("metadata", {})
            q = metadata.get("question", "")
            a = metadata.get("answer", "")
            if q and a:
                formatted_results += f"Q: {q}\nA: {a}\n\n"
        return formatted_results
    except Exception as e:
        console.print(f"[dim]Error getting FAQs: {str(e)}[/dim]")
        return ""

def get_relevant_symptoms(query: str, max_results: int = 3) -> str:
    if not hasattr(ai_client, 'vdb') or not ai_client.vdb:
        return ""
    try:
        results = ai_client.vdb.query("symptoms", query, n_results=max_results)
        if not results:
            return ""
        formatted_results = "Thông tin tham khảo về triệu chứng:\n\n"
        for result in results:
            metadata = result.get("metadata", {})
            symptom_name = metadata.get("symptom", "")
            description = metadata.get("description", "")
            if symptom_name:
                formatted_results += f"Triệu chứng: {symptom_name}\n"
            if description:
                formatted_results += f"Mô tả: {description}\n\n"
        return formatted_results
    except Exception as e:
        console.print(f"[dim]Error getting symptoms: {str(e)}[/dim]")
        return ""

# === UI DISPLAY ===
def display_available_commands():
    commands_panel = Panel(
        "[bold green]/help[/bold green] - Hiển thị danh sách lệnh khả dụng\n"
        "[bold green]/book[/bold green] - Bắt đầu quy trình đặt lịch khám\n"
        "[bold green]/history[/bold green] - Xem lịch sử hội thoại\n"
        "[bold green]/clear[/bold green] - Xóa màn hình\n"
        "[bold green]/exit[/bold green] - Thoát chương trình",
        title="[bold]Available Commands[/bold]",
        border_style="green",
        box=ROUNDED
    )
    console.print(commands_panel)
    console.print()

def display_welcome_message():
    today = datetime.now().strftime("%d/%m/%Y")
    console.print(Panel.fit(
        f"[bold blue]🏥 Medical Assistant CLI[/bold blue]\n"
        f"[italic]Trợ lý y tế thông minh[/italic]\n\n"
        f"📅 Hôm nay: [bold]{today}[/bold]",
        border_style="blue",
        box=ROUNDED,
        padding=(1, 2)
    ))

    if hasattr(ai_client, 'vdb') and ai_client.vdb:
        console.print(f"📚 Vector DB: [bold green]Connected[/bold green]")
    else:
        console.print(f"📚 Vector DB: [bold yellow]Not available[/bold yellow]")

    display_available_commands()

def display_help():
    table = Table(title="Các lệnh có sẵn", box=ROUNDED, border_style="green")
    table.add_column("Command", style="bold green")
    table.add_column("Description", style="white")

    table.add_row("/help", "Hiển thị danh sách lệnh khả dụng")
    table.add_row("/book", "Bắt đầu quy trình đặt lịch khám")
    table.add_row("/history", "Hiển thị lịch sử tương tác")
    table.add_row("/clear", "Xóa toàn bộ màn hình")
    table.add_row("/exit", "Thoát ứng dụng")

    console.print(table)

# === MAIN CHAT INTERFACE ===
def run_chat_interface():
    display_welcome_message()

    # Test TTS
    if TTS_AVAILABLE:
        with console.status("[bold blue]Đang kiểm tra hệ thống đọc tiếng Việt...[/bold blue]"):
            speak_text("Xin chào. Tôi là trợ lý y tế thông minh.", non_blocking=False)
            time.sleep(1)

    while True:
        user_input = Prompt.ask("\n[bold green]Bạn[/bold green]")

        # Commands
        if user_input.lower() == "/exit":
            console.print("[bold]Cảm ơn bạn đã sử dụng dịch vụ. Chúc bạn sức khỏe![/bold]")
            speak_text("Cảm ơn bạn đã sử dụng dịch vụ. Chúc bạn sức khỏe!")
            break
        elif user_input.lower() == "/help":
            display_help()
            continue
        elif user_input.lower() == "/clear":
            console.clear()
            display_welcome_message()
            continue
        elif user_input.lower() == "/history":
            if not conversation_history:
                console.print("[italic]Chưa có lịch sử tương tác.[/italic]")
            else:
                for msg in conversation_history[-10:]:
                    if msg["role"] == "user":
                        console.print(f"[bold green]Bạn:[/bold green] {msg['content']}")
                    else:
                        console.print(f"[bold blue]Bot:[/bold blue] {msg['content']}")
            continue
        elif user_input.lower().startswith("/book"):
            console.print("[italic]Bắt đầu quy trình đặt lịch khám...[/italic]")
            console.print("[italic]Tính năng đang phát triển. Vui lòng thử lại sau.[/italic]")
            continue

        # Add user message
        conversation_history.append({"role": "user", "content": user_input})

        with console.status("[bold blue]Đang suy nghĩ...[/bold blue]", spinner="dots"):
            faqs_info = get_relevant_faqs(user_input)
            symptoms_info = get_relevant_symptoms(user_input)

            console.print("[bold blue]Med Assistant:[/bold blue]", end=" ")
            full_response = ""

            for response_chunk in ai_client.generate_response_stream(user_input, conversation_history):
                full_response += response_chunk
                console.print(response_chunk, end="")
            print()

        # Save bot response
        conversation_history.append({"role": "assistant", "content": full_response})

        # TTS for response
        speak_text(full_response)

@app.command()
def main():
    """Start the medical assistant chatbot."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(project_root, "data"), exist_ok=True)

    try:
        run_chat_interface()
    except KeyboardInterrupt:
        console.print("\n[bold]Chương trình đã kết thúc. Cảm ơn bạn đã sử dụng dịch vụ![/bold]")
    except Exception as e:
        console.print(f"\n[bold red]Đã xảy ra lỗi: {str(e)}[/bold red]")

if __name__ == "__main__":
    app()
