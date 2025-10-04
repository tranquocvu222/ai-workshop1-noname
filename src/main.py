#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional
import json

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich import print as rprint
from dotenv import load_dotenv

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.scheduler import Scheduler
from src.ai.azure_client import AzureOpenAIClient

# Initialize Typer app
app = typer.Typer()

# Initialize Rich console
console = Console()

# Initialize scheduler and AI client
scheduler = Scheduler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/appointments.json"))
ai_client = AzureOpenAIClient()

# Store conversation history
conversation_history = []

def display_welcome_message():
    """Display welcome message with app info."""
    console.print(Panel.fit(
        "[bold blue]🏥 Medical Assistant CLI[/bold blue]\n"
        "[italic]Phòng khám đa khoa - Trợ lý thông minh[/italic]",
        border_style="blue"
    ))
    console.print("Nhập lệnh [bold green]/help[/bold green] để xem hướng dẫn sử dụng.")
    console.print()

def display_help():
    """Display help information and available commands."""
    table = Table(title="Available Commands", box=None)
    table.add_column("Command", style="green")
    table.add_column("Description")
    
    table.add_row("/help", "Hiển thị danh sách lệnh khả dụng")
    table.add_row("/history", "Hiển thị lịch sử tương tác trước đó")
    table.add_row("/clear", "Xóa toàn bộ màn hình CLI")
    table.add_row("/save last", "Lưu đoạn hội thoại cuối cùng ra file text")
    table.add_row("/check slots", "Kiểm tra lịch trống của từng khoa")
    table.add_row("/exit", "Thoát ứng dụng")
    
    console.print(table)

def display_departments():
    """Display available departments."""
    departments = scheduler.get_departments()
    
    table = Table(title="Danh sách khoa", box=None)
    table.add_column("Mã khoa", style="cyan")
    table.add_column("Tên khoa", style="green")
    table.add_column("Mô tả")
    
    for dept in departments:
        table.add_row(dept["code"], dept["name"], dept["description"])
    
    console.print(table)

def check_available_slots(date_str: Optional[str] = None, department: Optional[str] = None):
    """
    Check and display available slots for a specific date.
    
    Args:
        date_str: Date string in format YYYY-MM-DD (default: today)
        department: Optional department to filter by
    """
    # Use today's date if not specified
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Get available slots
        slots = scheduler.get_available_slots(date_str, department)
        
        # Display results
        console.print(f"\n📅 Date: [bold]{date_str}[/bold]\n")
        
        for dept, times in slots.items():
            emoji = "🩺" if dept == "Nội tổng hợp" else "🦷" if dept == "Răng hàm mặt" else "👁️" if dept == "Mắt" else "👂" if dept == "Tai mũi họng" else "👶" if dept == "Nhi khoa" else "🧬" if dept == "Da liễu" else "🏥"
            console.print(f"{emoji} Khoa {dept}:")
            
            if times:
                console.print(f"  ✅ Available: {', '.join(times)}")
            else:
                console.print("  ❌ No available slots")
                
        console.print()
        
    except Exception as e:
        console.print(f"[bold red]Error checking slots: {str(e)}[/bold red]")

def save_conversation():
    """Save the last conversation to a text file."""
    if not conversation_history:
        console.print("[yellow]No conversation to save.[/yellow]")
        return
    
    try:
        # Create directory if it doesn't exist
        os.makedirs("conversation_logs", exist_ok=True)
        
        # Generate filename with timestamp
        filename = f"conversation_logs/conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Write conversation to file
        with open(filename, "w", encoding="utf-8") as f:
            f.write("🏥 Medical Assistant CLI - Conversation Log\n\n")
            for msg in conversation_history:
                if msg["role"] == "user":
                    f.write(f"User: {msg['content']}\n\n")
                elif msg["role"] == "assistant":
                    f.write(f"Assistant: {msg['content']}\n\n")
        
        console.print(f"[green]Conversation saved to {filename}[/green]")
        
    except Exception as e:
        console.print(f"[bold red]Error saving conversation: {str(e)}[/bold red]")

def process_command(command: str) -> bool:
    """
    Process special commands.
    
    Args:
        command: User input command
        
    Returns:
        True if command was handled, False otherwise
    """
    # Strip leading '/' if present
    cmd = command.lstrip("/").lower().strip()
    
    if cmd == "help":
        display_help()
        return True
    
    elif cmd == "history":
        if not conversation_history:
            console.print("[yellow]No conversation history.[/yellow]")
        else:
            for i, msg in enumerate(conversation_history):
                if msg["role"] == "user":
                    console.print(f"[bold cyan]User:[/bold cyan] {msg['content']}")
                elif msg["role"] == "assistant":
                    console.print(f"[bold green]Assistant:[/bold green] {msg['content']}")
        return True
    
    elif cmd == "clear":
        os.system("cls" if os.name == "nt" else "clear")
        display_welcome_message()
        return True
    
    elif cmd == "save last":
        save_conversation()
        return True
    
    elif cmd == "check slots":
        # Ask for date
        date_str = Prompt.ask("Ngày (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
        
        # Ask for department (optional)
        display_departments()
        department = Prompt.ask("Tên khoa (để trống để xem tất cả)", default="")
        
        if not department:
            department = None
            
        check_available_slots(date_str, department)
        return True
        
    elif cmd == "exit":
        console.print("[yellow]Goodbye![/yellow]")
        sys.exit(0)
    
    return False

def process_user_input(user_input: str):
    """
    Process user input and generate appropriate response.
    
    Args:
        user_input: User's input text
    """
    # Check if input is a command
    if user_input.startswith("/"):
        if not process_command(user_input):
            console.print("[yellow]Unknown command. Type /help for available commands.[/yellow]")
        return
    
    # Store user message in history
    conversation_history.append({"role": "user", "content": user_input})
    
    # Generate response using Azure OpenAI
    response = ai_client.generate_response(user_input, conversation_history)
    
    # Store assistant response in history
    conversation_history.append({"role": "assistant", "content": response})
    
    # Display response
    console.print("\n[bold green]Assistant:[/bold green]")
    console.print(Markdown(response))
    console.print()

@app.command()
def main():
    """Main entry point for the Medical Assistant CLI."""
    # Display welcome message
    display_welcome_message()
    
    # Check if Azure OpenAI is configured
    if not ai_client.is_configured():
        console.print("[bold red]⚠️ Azure OpenAI is not properly configured. Please check your .env file.[/bold red]")
        console.print("You can still use appointment scheduling features, but AI-powered responses won't be available.")
    
    # Main interaction loop
    try:
        while True:
            # Get user input
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            # Process input
            process_user_input(user_input)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[bold red]An error occurred: {str(e)}[/bold red]")
        return 1
    
    return 0

if __name__ == "__main__":
    app()
