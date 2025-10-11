#!/usr/bin/env python3
import os
import sys
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.layout import Layout
from rich.box import Box, ROUNDED
from rich.style import Style
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

def display_welcome_message():
    """Display welcome message with app info."""
    today = datetime.now().strftime("%d/%m/%Y")
    console.print(Panel.fit(
        f"[bold blue]🏥 Medical Assistant CLI[/bold blue]\n"
        f"[italic]Phòng khám đa khoa - Trợ lý thông minh[/italic]\n\n"
        f"📅 Hôm nay: [bold]{today}[/bold]",
        border_style="blue",
        box=ROUNDED,
        padding=(1, 2)
    ))
    display_available_commands()

def display_available_commands():
    """Display available commands in a stylish menu."""
    commands_panel = Panel(
        "[bold green]/help[/bold green] - Hiển thị danh sách lệnh khả dụng\n"
        "[bold green]/book[/bold green] - Bắt đầu quy trình đặt lịch khám\n"
        "[bold green]/history[/bold green] - Hiển thị lịch sử tương tác trước đó\n"
        "[bold green]/clear[/bold green] - Xóa toàn bộ màn hình CLI\n"
        "[bold green]/save last[/bold green] - Lưu đoạn hội thoại cuối cùng ra file text\n"
        "[bold green]/check slots[/bold green] - Kiểm tra lịch trống của từng khoa\n"
        "[bold green]/my appointments[/bold green] - Xem lịch khám cá nhân\n"
        "[bold green]/exit[/bold green] - Thoát ứng dụng",
        title="[bold]Available Commands[/bold]",
        border_style="green",
        box=ROUNDED,
        padding=(0, 1)
    )
    console.print(commands_panel)
    console.print()

def display_help():
    """Display help information and available commands."""
    table = Table(title="Các lệnh có sẵn", box=ROUNDED, border_style="green")
    table.add_column("Command", style="bold green")
    table.add_column("Description", style="white")
    
    table.add_row("/help", "Hiển thị danh sách lệnh khả dụng")
    table.add_row("/book", "Bắt đầu quy trình đặt lịch khám")
    table.add_row("/history", "Hiển thị lịch sử tương tác trước đó")
    table.add_row("/clear", "Xóa toàn bộ màn hình CLI")
    table.add_row("/save last", "Lưu đoạn hội thoại cuối cùng ra file text")
    table.add_row("/check slots", "Kiểm tra lịch trống của từng khoa")
    table.add_row("/doctors", "Xem danh sách bác sĩ theo khoa")
    table.add_row("/my appointments", "Xem lịch khám cá nhân")
    table.add_row("/exit", "Thoát ứng dụng")
    
    console.print(table)

def display_departments():
    """Display available departments."""
    departments = scheduler.get_departments()
    
    table = Table(title="Danh sách khoa", box=ROUNDED, border_style="blue")
    table.add_column("Mã khoa", style="cyan bold")
    table.add_column("Tên khoa", style="green")
    table.add_column("Mô tả")
    
    for dept in departments:
        table.add_row(dept["code"], dept["name"], dept["description"])
    
    console.print(table)

def check_available_slots(date_str: Optional[str] = None, department: Optional[str] = None):
    """
    Check and display available slots for a specific date.
    
    Args:
        date_str: Date string in format YYYY-MM-DD or natural language (default: today)
        department: Optional department to filter by
    """
    # Use today's date if not specified
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    else:
        # Parse natural language date expressions
        date_str = scheduler.parse_date_expression(date_str)
    
    # Check if date is in the past
    if not scheduler.is_valid_date(date_str):
        console.print(Panel(
            "Không thể kiểm tra lịch khám cho ngày trong quá khứ. Đã tự động chọn ngày hôm nay.",
            title="[bold]Warning[/bold]",
            border_style="yellow",
            box=ROUNDED
        ))
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Get available slots
        slots = scheduler.get_available_slots(date_str, department)
        
        # Get formatted date with weekday
        formatted_date = scheduler.format_date_with_weekday(date_str)
        
        # Display results
        console.print(Panel(
            f"Date: [bold]{formatted_date}[/bold]",
            title="[bold]Available Slots[/bold]",
            border_style="cyan",
            box=ROUNDED
        ))
        
        table = Table(box=ROUNDED, border_style="blue")
        table.add_column("Department", style="bold cyan")
        table.add_column("Available Slots", style="green")
        
        for dept, times in slots.items():
            emoji = "🩺" if dept == "Nội tổng hợp" else "🦷" if dept == "Răng hàm mặt" else "👁️" if dept == "Mắt" else "👂" if dept == "Tai mũi họng" else "👶" if dept == "Nhi khoa" else "🧬" if dept == "Da liễu" else "🏥"
            
            if times:
                table.add_row(f"{emoji} {dept}", ", ".join(times))
            else:
                table.add_row(f"{emoji} {dept}", "[bold red]No available slots[/bold red]")
                
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(Panel(
            f"Error checking slots: {str(e)}",
            title="[bold]Error[/bold]",
            border_style="red",
            box=ROUNDED
        ))

def save_conversation():
    """Save the last conversation to a text file."""
    if not conversation_history:
        console.print(Panel(
            "No conversation to save.",
            title="[bold]Info[/bold]",
            border_style="yellow",
            box=ROUNDED
        ))
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
        
        console.print(Panel(
            f"Conversation saved to {filename}",
            title="[bold]Success[/bold]",
            border_style="green",
            box=ROUNDED
        ))
        
    except Exception as e:
        console.print(Panel(
            f"Error saving conversation: {str(e)}",
            title="[bold]Error[/bold]",
            border_style="red",
            box=ROUNDED
        ))

def display_doctors(doctors: List[Dict[str, str]]):
    """
    Display available doctors in a formatted table.
    
    Args:
        doctors: List of doctor information dictionaries
    """
    if not doctors:
        console.print(Panel(
            "No doctors available.",
            title="[bold]Info[/bold]",
            border_style="yellow",
            box=ROUNDED
        ))
        return
    
    # Check for error entries
    error_doctors = [doc for doc in doctors if "error" in doc]
    if error_doctors:
        for doc in error_doctors:
            console.print(Panel(
                doc["error"],
                title="[bold]Error[/bold]",
                border_style="red",
                box=ROUNDED
            ))
        return
    
    table = Table(title="Danh sách bác sĩ", box=ROUNDED, border_style="blue")
    table.add_column("ID", style="bold cyan")
    table.add_column("Tên bác sĩ", style="bold green")
    table.add_column("Chuyên khoa", style="magenta")
    table.add_column("Kinh nghiệm", style="yellow")
    table.add_column("Học vấn", style="blue italic")
    
    for doctor in doctors:
        table.add_row(
            doctor.get("id", "N/A"),
            doctor.get("name", "N/A"),
            doctor.get("specialty", "N/A"),
            doctor.get("experience", "N/A"),
            doctor.get("education", "N/A") if "education" in doctor else ""
        )
    
    console.print(table)

def display_symptom_analysis(analysis: Dict[str, Any]):
    """
    Display symptom analysis results in a formatted panel.
    
    Args:
        analysis: Dictionary with analysis results
    """
    if "error" in analysis:
        console.print(Panel(
            f"Error analyzing symptoms: {analysis['error']}",
            title="[bold]Error[/bold]",
            border_style="red",
            box=ROUNDED
        ))
        return
    
    # Create a table for better formatting
    table = Table(box=ROUNDED, border_style="blue", expand=True)
    table.add_column("Phân tích", style="bold cyan")
    table.add_column("Kết quả", style="white")
    
    # Add departments
    if "departments" in analysis and analysis["departments"]:
        departments_list = ", ".join(analysis["departments"])
        table.add_row("Chuyên khoa phù hợp", f"[bold green]{departments_list}[/bold green]")
    
    # Add possible conditions
    if "possible_conditions" in analysis and analysis["possible_conditions"]:
        conditions_list = ", ".join(analysis["possible_conditions"])
        table.add_row("Bệnh lý tiềm năng", f"[bold yellow]{conditions_list}[/bold yellow]")
    
    # Add severity
    if "severity" in analysis:
        severity = analysis["severity"]
        severity_color = "green" if severity == "Thấp" else "yellow" if severity == "Trung bình" else "red"
        table.add_row("Mức độ nghiêm trọng", f"[bold {severity_color}]{severity}[/bold {severity_color}]")
    
    # Add recommendation
    if "recommendation" in analysis:
        table.add_row("Lời khuyên", f"[bold blue]{analysis['recommendation']}[/bold blue]")
    
    # Create panel with the table
    panel = Panel(
        table,
        title="[bold]Phân tích triệu chứng[/bold]",
        border_style="blue",
        box=ROUNDED,
        padding=(1, 1)
    )
    console.print(panel)

def view_my_appointments():
    """View and display all appointments for the current patient."""
    patient_name = Prompt.ask("[bold cyan]Vui lòng nhập tên của bạn để xem lịch khám[/bold cyan]")
    
    appointments = scheduler.get_appointments_for_patient(patient_name)
    
    if not appointments:
        console.print(Panel(
            f"Không tìm thấy lịch khám nào cho bệnh nhân '{patient_name}'.",
            title="[bold]Info[/bold]",
            border_style="yellow",
            box=ROUNDED
        ))
        return
    
    table = Table(title=f"Lịch khám của {patient_name}", box=ROUNDED, border_style="blue")
    table.add_column("Ngày", style="bold cyan")
    table.add_column("Giờ", style="bold green")
    table.add_column("Khoa", style="magenta")
    table.add_column("Bác sĩ", style="yellow")
    table.add_column("Ghi chú", style="italic")
    
    for appt in appointments:
        table.add_row(
            appt.get("date", "N/A"),
            appt.get("time", "N/A"),
            appt.get("department", "N/A"),
            appt.get("doctor", "N/A"),
            appt.get("notes", "")
        )
    
    console.print(table)

def reset_booking():
    """Reset booking information."""
    global current_booking
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

def start_booking_process():
    """Start the appointment booking process."""
    global current_booking
    
    # Reset any previous booking information
    reset_booking()
    
    # Set booking in progress
    current_booking["in_progress"] = True
    
    today = datetime.now().strftime("%d/%m/%Y")
    
    console.print(Panel(
        f"Vui lòng trả lời các câu hỏi sau để đặt lịch khám.\n"
        f"📅 Hôm nay là: [bold]{today}[/bold]",
        title="[bold]🏥 Quy trình đặt lịch khám[/bold]",
        border_style="blue",
        box=ROUNDED,
        padding=(1, 2)
    ))
    
    # Get patient name
    current_booking["patient"] = Prompt.ask("[bold cyan]Họ tên bệnh nhân[/bold cyan]")
    
    # Get symptoms
    current_booking["symptoms"] = Prompt.ask("[bold cyan]Mô tả triệu chứng của bạn[/bold cyan]")
    
    # Analyze symptoms
    console.print("[italic]Đang phân tích triệu chứng...[/italic]")
    analysis = ai_client.analyze_symptoms(current_booking["symptoms"])
    
    # Display analysis results
    display_symptom_analysis(analysis)
    
    # Get suggested departments
    suggested_departments = analysis.get("departments", [])
    suggested_dept_codes = analysis.get("department_codes", [])
    
    # If no departments were suggested, ask user to select one
    if not suggested_departments:
        console.print(Panel(
            "Không thể xác định khoa phù hợp từ triệu chứng. Vui lòng chọn khoa:",
            border_style="yellow",
            box=ROUNDED
        ))
        display_departments()
        dept_code = Prompt.ask("[bold cyan]Mã khoa (ví dụ: D01)[/bold cyan]", default="D01")
        dept = scheduler.get_department_by_code(dept_code)
        
        if dept:
            current_booking["department"] = dept["name"]
            current_booking["department_code"] = dept["code"]
        else:
            console.print(Panel(
                "Mã khoa không hợp lệ. Quy trình đặt lịch bị hủy.",
                title="[bold]Error[/bold]",
                border_style="red",
                box=ROUNDED
            ))
            reset_booking()
            return
    else:
        # Ask user to select from suggested departments
        console.print(Panel(
            "Vui lòng chọn khoa phù hợp với tình trạng của bạn:",
            title="[bold]Chọn khoa phù hợp[/bold]",
            border_style="blue",
            box=ROUNDED
        ))
        
        dept_table = Table(box=ROUNDED, border_style="blue")
        dept_table.add_column("#", style="bold cyan")
        dept_table.add_column("Khoa", style="bold green")
        dept_table.add_column("Mã", style="yellow")
        
        for i, dept in enumerate(suggested_departments):
            dept_code = suggested_dept_codes[i] if i < len(suggested_dept_codes) else f"D0{i+1}"
            dept_table.add_row(str(i+1), dept, dept_code)
        
        console.print(dept_table)
        
        choice = Prompt.ask(
            "[bold cyan]Chọn số tương ứng[/bold cyan]",
            default="1",
            choices=[str(i+1) for i in range(len(suggested_departments))]
        )
        
        # Set selected department
        idx = int(choice) - 1
        current_booking["department"] = suggested_departments[idx]
        current_booking["department_code"] = (
            suggested_dept_codes[idx] if idx < len(suggested_dept_codes) 
            else f"D0{idx+1}"
        )
    
    # Get doctor suggestions for the selected department
    console.print(Panel(
        f"Đang tìm bác sĩ phù hợp tại khoa {current_booking['department']}...",
        border_style="blue",
        box=ROUNDED,
        padding=(0, 1)
    ))
    doctors = ai_client.get_doctor_suggestions(current_booking["department_code"])
    
    # Display doctors and ask user to select one
    display_doctors(doctors)
    
    # Check if there are valid doctors to select
    valid_doctors = [doc for doc in doctors if "error" not in doc]
    
    if valid_doctors:
        doctor_choice = Prompt.ask(
            "[bold cyan]Chọn ID bác sĩ[/bold cyan]",
            default=valid_doctors[0].get("id", "BS001") if valid_doctors else "BS001"
        )
        
        # Find selected doctor
        selected_doctor = next((doc for doc in doctors if doc.get("id") == doctor_choice), None)
        if selected_doctor:
            current_booking["doctor"] = selected_doctor.get("name")
        else:
            current_booking["doctor"] = f"BS. {doctor_choice}"
    else:
        current_booking["doctor"] = "BS. Chưa xác định"
        console.print(Panel(
            "Không tìm thấy thông tin bác sĩ. Sử dụng thông tin mặc định.",
            border_style="yellow",
            box=ROUNDED
        ))
    
    # Get appointment date
    date_input = Prompt.ask(
        "[bold cyan]Ngày khám (có thể nhập: ngày mai, mốt, DD/MM/YYYY, YYYY-MM-DD)[/bold cyan]", 
        default="ngày mai"
    )
    
    # Parse natural language date
    parsed_date = scheduler.parse_date_expression(date_input)
    
    # Check if date is in the past
    if not scheduler.is_valid_date(parsed_date):
        console.print(Panel(
            "Không thể đặt lịch cho ngày trong quá khứ. Đã tự động chọn ngày mai.",
            title="[bold]Warning[/bold]",
            border_style="yellow",
            box=ROUNDED
        ))
        parsed_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    formatted_date = scheduler.format_date_with_weekday(parsed_date)
    
    console.print(f"[green]Đã chọn: {formatted_date}[/green]")
    current_booking["date"] = parsed_date
    
    # Check available slots for the selected date and department
    available_slots = scheduler.get_available_slots(current_booking["date"], current_booking["department"])
    
    if current_booking["department"] not in available_slots or not available_slots[current_booking["department"]]:
        console.print(Panel(
            "Không có khung giờ trống cho ngày và khoa đã chọn. Vui lòng thử lại với ngày khác.",
            title="[bold]Error[/bold]",
            border_style="red",
            box=ROUNDED
        ))
        reset_booking()
        return
    
    # Display available slots and ask user to select one
    console.print(Panel(
        f"Vui lòng chọn khung giờ phù hợp:",
        title=f"[bold]Khung giờ trống cho ngày {current_booking['date']}[/bold]",
        border_style="blue",
        box=ROUNDED
    ))
    
    slots = available_slots[current_booking["department"]]
    
    slot_table = Table(box=ROUNDED, border_style="blue")
    slot_table.add_column("#", style="bold cyan")
    slot_table.add_column("Giờ", style="bold green")
    
    for i, slot in enumerate(slots):
        slot_table.add_row(str(i+1), slot)
    
    console.print(slot_table)
    
    slot_choice = Prompt.ask(
        "[bold cyan]Chọn số tương ứng[/bold cyan]",
        default="1",
        choices=[str(i+1) for i in range(len(slots))]
    )
    
    # Set selected time slot
    current_booking["time"] = slots[int(slot_choice) - 1]
    
    # Optional notes
    current_booking["notes"] = Prompt.ask("[bold cyan]Ghi chú (nếu có)[/bold cyan]", default="")
    
    # Confirmation
    confirmation_table = Table(title="Thông tin đặt lịch khám", box=ROUNDED, border_style="blue", expand=True)
    confirmation_table.add_column("Thông tin", style="bold cyan")
    confirmation_table.add_column("Chi tiết", style="white")
    
    confirmation_table.add_row("Bệnh nhân", current_booking["patient"])
    confirmation_table.add_row("Khoa", f"{current_booking['department']} ({current_booking['department_code']})")
    confirmation_table.add_row("Bác sĩ", current_booking["doctor"])
    confirmation_table.add_row("Ngày khám", scheduler.format_date_with_weekday(current_booking["date"]))
    confirmation_table.add_row("Giờ khám", current_booking["time"])
    if current_booking["notes"]:
        confirmation_table.add_row("Ghi chú", current_booking["notes"])
    
    console.print(confirmation_table)
    
    confirmed = Confirm.ask("\nXác nhận đặt lịch khám?", default=True)
    
    if confirmed:
        # Add appointment to scheduler
        success = scheduler.add_appointment(
            department=current_booking["department"],
            doctor=current_booking["doctor"],
            date=current_booking["date"],
            time=current_booking["time"],
            patient=current_booking["patient"],
            notes=current_booking["notes"]
        )
        
        if success:
            console.print(Panel(
                "✓ Đặt lịch khám thành công!",
                title="[bold]Success[/bold]",
                border_style="green",
                box=ROUNDED
            ))
        else:
            console.print(Panel(
                "✗ Đặt lịch khám thất bại. Khung giờ đã được đặt trước đó.",
                title="[bold]Error[/bold]",
                border_style="red",
                box=ROUNDED
            ))
    else:
        console.print(Panel(
            "Đã hủy đặt lịch khám.",
            title="[bold]Info[/bold]",
            border_style="yellow",
            box=ROUNDED
        ))
    
    # Reset booking
    reset_booking()

def display_department_doctors(department_code: str):
    """Display doctors for a specific department."""
    doctors = ai_client.get_doctor(department_code=department_code)
    if doctors:
        display_doctors(doctors)
    else:
        console.print(Panel(
            "Không tìm thấy thông tin bác sĩ cho khoa này.",
            title="[bold]Info[/bold]",
            border_style="yellow",
            box=ROUNDED
        ))

def recommend_doctors_based_on_symptoms(symptoms: str):
    """
    Analyze symptoms and suggest appropriate doctors.
    
    Args:
        symptoms: Description of symptoms
    """
    console.print("[italic]Đang phân tích triệu chứng...[/italic]")
    
    # Analyze symptoms to get recommended departments
    analysis = ai_client.analyze_symptoms(symptoms)
    
    if "error" in analysis:
        console.print(Panel(
            f"Không thể phân tích triệu chứng: {analysis['error']}",
            title="[bold]Error[/bold]",
            border_style="red",
            box=ROUNDED
        ))
        return
    
    # Display analysis results
    display_symptom_analysis(analysis)
    
    # Get department codes from analysis
    department_codes = analysis.get("department_codes", [])
    if not department_codes and "departments" in analysis:
        # Try to map department names to codes
        departments = scheduler.get_departments()
        dept_map = {dept["name"].lower(): dept["code"] for dept in departments}
        
        for dept_name in analysis.get("departments", []):
            if dept_name.lower() in dept_map:
                department_codes.append(dept_map[dept_name.lower()])
    
    if not department_codes:
        console.print(Panel(
            "Không thể xác định khoa phù hợp từ triệu chứng.",
            title="[bold]Warning[/bold]",
            border_style="yellow",
            box=ROUNDED
        ))
        return
    
    # For each department code, get and display doctors using the new get_doctor function
    console.print(Panel(
        "Dựa trên triệu chứng của bạn, tôi gợi ý các bác sĩ sau:",
        title="[bold]Gợi ý bác sĩ[/bold]",
        border_style="blue",
        box=ROUNDED
    ))
    
    for dept_code in department_codes[:2]:  # Limit to top 2 departments to avoid information overload
        dept_name = scheduler.get_department_name(dept_code)
        console.print(f"\n[bold cyan]Khoa {dept_name} ({dept_code}):[/bold cyan]")
        doctors = ai_client.get_doctor(department_code=dept_code)
        display_doctors(doctors)

def suggest_related_command(user_input: str) -> Optional[str]:
    """
    Suggest a related command based on user input.
    
    Args:
        user_input: User's input text
        
    Returns:
        Suggested command or None if no matching command found
    """
    # Map keywords to commands
    keyword_map = {
        "đặt lịch": "/book",
        "lịch khám": "/book",
        "book": "/book",
        "booking": "/book",
        "đăng ký khám": "/book",
        "đăng ký": "/book",
        "hẹn khám": "/book",
        "slot": "/check slots",
        "khung giờ": "/check slots",
        "giờ trống": "/check slots",
        "lịch trống": "/check slots",
        "available": "/check slots",
        "trống": "/check slots",
        "ngày nào": "/check slots",
        "lịch của tôi": "/my appointments", 
        "lịch cá nhân": "/my appointments",
        "lịch đã đặt": "/my appointments",
        "hẹn": "/my appointments",
        "trợ giúp": "/help",
        "hướng dẫn": "/help",
        "giúp đỡ": "/help",
        "help": "/help",
        "lưu": "/save last",
        "save": "/save last",
        "history": "/history",
        "lịch sử": "/history"
    }
    
    # Check for matches
    lower_input = user_input.lower()
    for keyword, command in keyword_map.items():
        if keyword in lower_input:
            return command
    
    return None

def process_user_input(user_input: str):
    """
    Process user input and generate appropriate response.
    
    Args:
        user_input: User's input text
    """
    # Check if input is a command
    if user_input.startswith("/"):
        if not process_command(user_input):
            console.print(Panel(
                "Unknown command. Type /help for available commands.",
                title="[bold]Info[/bold]",
                border_style="yellow",
                box=ROUNDED
            ))
        else:
            # Always display available commands after processing a command
            display_available_commands()
        return
    
    # Check for direct department-specific doctor queries
    department_doctor_patterns = [
        r"(bác sĩ|doctor|bs).*(khoa|chuyên khoa|department) ([\w\s]+)(?!\?)",
        r"(bác sĩ|doctor|bs).*(về|chuyên về|chữa|khám) ([\w\s]+)(?!\?)",
        r"ai.*(khám|chữa) ([\w\s]+)(?!\?)",
        r"(bác sĩ|doctor) nào.*(phù hợp|thích hợp).*(khoa|chuyên khoa) ([\w\s]+)(?!\?)"
    ]
    
    # Department name mapping for direct queries
    department_keywords = {
        'nội': 'D01',
        'răng': 'D02',
        'hàm mặt': 'D02',
        'tai': 'D03',
        'mũi': 'D03', 
        'họng': 'D03',
        'tai mũi họng': 'D03',
        'mắt': 'D04',
        'nhãn khoa': 'D04',
        'da': 'D05',
        'da liễu': 'D05',
        'nhi': 'D06',
        'trẻ em': 'D06'
    }
    
    # Check if query is asking for doctors in a specific department
    matched_dept_code = None
    for pattern in department_doctor_patterns:
        match = re.search(pattern, user_input.lower())
        if match:
            # Extract potential department name
            potential_dept = match.group(len(match.groups()))
            # Try to find a matching department
            for keyword, code in department_keywords.items():
                if keyword in potential_dept.lower():
                    matched_dept_code = code
                    break
    
    if matched_dept_code:
        dept_info = scheduler.get_department_by_code(matched_dept_code)
        if dept_info:
            console.print(Panel(
                f"Đang tìm thông tin bác sĩ khoa {dept_info['name']}...",
                title="[bold]Thông tin bác sĩ[/bold]",
                border_style="blue",
                box=ROUNDED
            ))
            
            # Store interaction in history
            conversation_history.append({"role": "user", "content": user_input})
            
            # Display doctors using function call directly
            doctors = ai_client.get_doctor(department_code=matched_dept_code)
            
            # Format the response
            if doctors:
                # Create doctor info response
                result = f"Dựa trên yêu cầu của bạn, đây là các bác sĩ phù hợp tại khoa {dept_info['name']}:\n\n"
                for doc in doctors:
                    result += f"- {doc.get('name', 'N/A')} ({doc.get('id', 'N/A')})\n"
                    result += f"  Chuyên khoa: {doc.get('specialty', 'N/A')}\n"
                    result += f"  Kinh nghiệm: {doc.get('experience', 'N/A')}\n"
                    result += f"  Học vấn: {doc.get('education', 'N/A')}\n\n"
                
                # Store the response in history
                conversation_history.append({"role": "assistant", "content": result})
                
                # Display response and doctors
                console.print("\n[bold green]Assistant:[/bold green]")
                console.print(result)
                
                # Ask if user wants to book an appointment
                if Confirm.ask("\nBạn có muốn đặt lịch khám với một trong những bác sĩ này không?", default=False):
                    start_booking_process()
            else:
                response = f"Tôi không tìm thấy bác sĩ nào cho khoa {dept_info['name']}."
                conversation_history.append({"role": "assistant", "content": response})
                console.print("\n[bold green]Assistant:[/bold green]")
                console.print(response)
            
            display_available_commands()
            return
    
    # Check for doctor recommendation request that needs symptom analysis
    doctor_recommendation_patterns = [
        r"(gợi ý|giới thiệu|tư vấn|suggest|recommend).*(bác sĩ|doctor|bs)",
        r"(bác sĩ|doctor|bs).*(phù hợp|thích hợp|nên gặp|nên khám).*\?",
        r"(ai|bác sĩ nào|doctor).*(khám|chữa|điều trị).*\?",
        r"(triệu chứng).*(bác sĩ|doctor|bs)",
        r"(bác sĩ).*(triệu chứng|symptom)",
        r"(danh sách|list) (bác sĩ|bac si|doctor)",
    ]
    
    if any(re.search(pattern, user_input.lower()) for pattern in doctor_recommendation_patterns):
        # Extract symptoms from user input or ask for them
        symptoms_match = re.search(r"(triệu chứng|symptom).*(là|như|gồm|:)(.+)", user_input.lower())
        
        if symptoms_match:
            symptoms = symptoms_match.group(3).strip()
            recommend_doctors_based_on_symptoms(symptoms)
        else:
            symptoms = Prompt.ask("[bold cyan]Vui lòng mô tả triệu chứng của bạn[/bold cyan]")
            recommend_doctors_based_on_symptoms(symptoms)
        
        # Store interaction in history
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({
            "role": "assistant", 
            "content": "Tôi đã phân tích triệu chứng và gợi ý các bác sĩ phù hợp cho bạn."
        })
        
        display_available_commands()
        return
    
    # Check for booking intent in natural language
    booking_patterns = [
        r"đặt (lịch|lich) khám",
        r"muốn đặt (lịch|lich)",
        r"(book|booking) (appointment|lịch)",
        r"đăng ký khám",
        r"lấy (lịch|lich) khám"
    ]
    
    # Check if there's a related command suggestion
    suggested_command = suggest_related_command(user_input)
    
    if any(re.search(pattern, user_input.lower()) for pattern in booking_patterns):
        console.print(Panel(
            "Phát hiện yêu cầu đặt lịch khám. Bắt đầu quy trình đặt lịch.",
            title="[bold]Info[/bold]",
            border_style="blue",
            box=ROUNDED
        ))
        start_booking_process()
        display_available_commands()
        return
    elif suggested_command:
        console.print(Panel(
            f"Tôi thấy bạn đang muốn sử dụng lệnh {suggested_command}. Bạn có thể gõ lệnh này trực tiếp.",
            title="[bold]Gợi ý[/bold]",
            border_style="cyan",
            box=ROUNDED
        ))
    
    # Check for date/time related expressions and add context
    date_patterns = [
        r'(hôm nay|ngày mai|ngày mốt|ngày kia)',
        r'(thứ \d|thứ [a-zA-Z]+|chủ nhật)',
        r'\d{1,2}/\d{1,2}',
        r'\d{1,2}/\d{1,2}/\d{4}'
    ]
    
    for pattern in date_patterns:
        if re.search(pattern, user_input.lower()):
            today = datetime.now().strftime("%d/%m/%Y")
            user_input = f"Hôm nay là {today}. {user_input}"
            break
    
    # Check if user is asking specifically about doctors
    if "bác sĩ" in user_input.lower() or "doctor" in user_input.lower() or "bs" in user_input.lower():
        # For function calling, we don't need to add this additional context
        # The model will use the getDoctor function automatically
        pass
    
    # Store user message in history
    conversation_history.append({"role": "user", "content": user_input})
    
    # Display assistant header
    console.print("\n[bold green]Assistant:[/bold green]")
    
    # Use streaming response
    full_response = ""
    function_call_detected = False
    
    try:
        # Get the stream generator
        response_stream = ai_client.generate_response_stream(user_input, conversation_history)
        
        # Process and display chunks as they arrive
        for chunk in response_stream:
            if "Đang tìm kiếm thông tin bác sĩ" in chunk:
                function_call_detected = True
                console.print(chunk, end="")
                sys.stdout.flush()
            else:
                full_response += chunk
                # Display each chunk as it arrives (mimicking streaming)
                console.print(chunk, end="")
                sys.stdout.flush()
            
        # Add a newline after response is complete
        console.print()
        console.print()
        
        # Store the full response in history
        conversation_history.append({"role": "assistant", "content": full_response})
        
        # Display available commands after each response
        display_available_commands()
    
    except Exception as e:
        error_msg = f"Hệ thống hiện đang gặp sự cố: {str(e)}. Vui lòng thử lại sau ít phút."
        console.print(Panel(
            error_msg,
            title="[bold]Thông báo[/bold]",
            border_style="yellow",
            box=ROUNDED
        ))
        # Store error message in history
        conversation_history.append({"role": "assistant", "content": error_msg})
        
        # Display available commands even after error
        display_available_commands()

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
    
    elif cmd == "book":
        start_booking_process()
        return True
    
    elif cmd == "doctors" or cmd == "list doctors":
        # First check if user wants recommendations based on symptoms
        if Confirm.ask("Bạn muốn được gợi ý bác sĩ dựa trên triệu chứng?", default=True):
            symptoms = Prompt.ask("[bold cyan]Vui lòng mô tả triệu chứng của bạn[/bold cyan]")
            recommend_doctors_based_on_symptoms(symptoms)
        else:
            # Display departments first
            display_departments()
            
            # Ask for department
            dept_code = Prompt.ask(
                "[bold cyan]Vui lòng chọn mã khoa để xem danh sách bác sĩ (vd: D01)[/bold cyan]",
                default="D01"
            )
            
            # Display doctors for selected department
            display_department_doctors(dept_code)
        return True
    
    # ...existing code...

@app.command()
def main():
    """Main entry point for the Medical Assistant CLI."""
    # Display welcome message
    display_welcome_message()
    
    # Check if Azure OpenAI is configured
    if not ai_client.is_configured():
        console.print(Panel(
            "⚠️ Azure OpenAI is not properly configured. Please check your .env file.\n"
            "You can still use appointment scheduling features, but AI-powered responses won't be available.",
            title="[bold]Warning[/bold]",
            border_style="red",
            box=ROUNDED
        ))
    
    # Main interaction loop
    try:
        while True:
            # Get user input
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            # Process input
            process_user_input(user_input)
            
    except KeyboardInterrupt:
        console.print(Panel(
            "Goodbye!",
            title="[bold]Info[/bold]",
            border_style="yellow",
            box=ROUNDED
        ))
    except Exception as e:
        console.print(Panel(
            f"An error occurred: {str(e)}",
            title="[bold]Error[/bold]",
            border_style="red",
            box=ROUNDED
        ))
        return 1
    
    return 0

if __name__ == "__main__":
    app()
