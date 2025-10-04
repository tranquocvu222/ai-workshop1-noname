import json
import os
import re
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any

class Scheduler:
    """Handles appointment scheduling and slot availability checking."""
    
    def __init__(self, data_file: str = "../data/appointments.json"):
        """Initialize scheduler with path to appointments data file."""
        self.data_file = data_file
        self.appointments = []
        self._load_appointments()
        
        # Default time slots (8:00 to 16:00, every 30 minutes)
        self.default_slots = [
            f"{h:02d}:{m:02d}" 
            for h in range(8, 17) 
            for m in [0, 30] 
            if not (h == 16 and m == 30)
        ]
        
    def _load_appointments(self) -> None:
        """Load appointments from JSON file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.appointments = data.get("appointments", [])
            else:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
                # Create empty appointments file
                self.save_appointments()
        except Exception as e:
            print(f"Error loading appointments: {e}")
            self.appointments = []
    
    def save_appointments(self) -> None:
        """Save appointments to JSON file."""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({"appointments": self.appointments}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving appointments: {e}")
    
    def get_available_slots(self, date: str, department: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get available appointment slots for a specific date and optional department.
        
        Args:
            date: Date string in format YYYY-MM-DD
            department: Optional department name to filter by
            
        Returns:
            Dictionary mapping department names to lists of available time slots
        """
        # Get all booked slots for the date
        booked_slots = {
            (appt["department"], appt["time"]) 
            for appt in self.appointments 
            if appt["date"] == date and (department is None or appt["department"] == department)
        }
        
        # Group departments
        departments = {
            appt["department"] for appt in self.appointments 
            if department is None or appt["department"] == department
        }
        
        # If specified department doesn't exist in appointments, add it
        if department and not departments:
            departments.add(department)
        
        # Calculate available slots for each department
        available_slots = {}
        for dept in departments:
            dept_booked_times = {time for (dept_name, time) in booked_slots if dept_name == dept}
            available_slots[dept] = [slot for slot in self.default_slots if slot not in dept_booked_times]
            
        return available_slots
    
    def add_appointment(self, department: str, doctor: str, date: str, time: str, patient: str, notes: str = "") -> bool:
        """
        Add a new appointment to the schedule.
        
        Args:
            department: Department name
            doctor: Doctor name
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            patient: Patient name
            notes: Optional appointment notes
            
        Returns:
            True if appointment was added successfully, False otherwise
        """
        # Check if slot is available
        available_slots = self.get_available_slots(date, department)
        if department not in available_slots or time not in available_slots[department]:
            return False
        
        # Add appointment
        self.appointments.append({
            "department": department,
            "doctor": doctor,
            "date": date,
            "time": time,
            "patient": patient,
            "notes": notes
        })
        
        # Save changes
        self.save_appointments()
        return True
    
    def get_departments(self) -> List[Dict[str, str]]:
        """
        Get list of department information.
        
        Returns:
            List of dictionaries with department information
        """
        return [
            {"code": "D01", "name": "Nội tổng hợp", "description": "Khám tổng quát, điều trị các bệnh thông thường"},
            {"code": "D02", "name": "Răng hàm mặt", "description": "Chăm sóc răng miệng, chỉnh nha, tiểu phẫu"},
            {"code": "D03", "name": "Tai mũi họng", "description": "Khám, điều trị các bệnh lý về tai, mũi, họng"},
            {"code": "D04", "name": "Mắt", "description": "Khám thị lực, điều trị cận thị, loạn thị"},
            {"code": "D05", "name": "Da liễu", "description": "Điều trị mụn, viêm da, dị ứng, lão hóa"},
            {"code": "D06", "name": "Nhi khoa", "description": "Khám trẻ em, tư vấn dinh dưỡng, tiêm chủng"}
        ]
    
    def get_department_by_code(self, code: str) -> Optional[Dict[str, str]]:
        """
        Get department information by code.
        
        Args:
            code: Department code (e.g., 'D01')
            
        Returns:
            Department information dictionary or None if not found
        """
        departments = self.get_departments()
        for dept in departments:
            if dept["code"] == code:
                return dept
        return None
    
    def get_appointments_for_patient(self, patient_name: str) -> List[Dict[str, Any]]:
        """
        Get all appointments for a specific patient.
        
        Args:
            patient_name: Name of the patient
            
        Returns:
            List of appointment dictionaries
        """
        return [
            appt for appt in self.appointments
            if appt["patient"].lower() == patient_name.lower()
        ]
    
    def parse_date_expression(self, date_expr: str) -> str:
        """
        Parse natural language date expressions into YYYY-MM-DD format.
        
        Args:
            date_expr: Natural language date expression (e.g., 'tomorrow', 'next Monday')
            
        Returns:
            Date string in format YYYY-MM-DD
        """
        today = datetime.now()
        date_expr = date_expr.lower().strip()
        
        # Direct date format (YYYY-MM-DD)
        if re.match(r'\d{4}-\d{2}-\d{2}', date_expr):
            try:
                input_date = datetime.strptime(date_expr, '%Y-%m-%d')
                # Check if date is in the past
                if input_date.date() < today.date():
                    return today.strftime('%Y-%m-%d')
                return date_expr
            except ValueError:
                return today.strftime('%Y-%m-%d')
        
        # Date format DD/MM/YYYY
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_expr):
            parts = date_expr.split('/')
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            try:
                input_date = datetime(year, month, day)
                # Check if date is in the past
                if input_date.date() < today.date():
                    return today.strftime('%Y-%m-%d')
                return input_date.strftime('%Y-%m-%d')
            except ValueError:
                return today.strftime('%Y-%m-%d')  # Return today's date if invalid
        
        # Common natural language expressions
        if date_expr in ['today', 'hôm nay', 'ngày hôm nay']:
            return today.strftime('%Y-%m-%d')
        
        if date_expr in ['tomorrow', 'ngày mai', 'mai', 'next day']:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        
        if date_expr in ['day after tomorrow', 'ngày mốt', 'mốt', 'ngày kia']:
            return (today + timedelta(days=2)).strftime('%Y-%m-%d')
        
        # Next weekday expressions
        weekdays = {
            'monday': 0, 'thứ hai': 0, 'thứ 2': 0,
            'tuesday': 1, 'thứ ba': 1, 'thứ 3': 1,
            'wednesday': 2, 'thứ tư': 2, 'thứ 4': 2,
            'thursday': 3, 'thứ năm': 3, 'thứ 5': 3,
            'friday': 4, 'thứ sáu': 4, 'thứ 6': 4,
            'saturday': 5, 'thứ bảy': 5, 'thứ 7': 5,
            'sunday': 6, 'chủ nhật': 6, 'cn': 6
        }
        
        for day_name, day_num in weekdays.items():
            if f"next {day_name}" in date_expr or f"thứ {day_name}" in date_expr:
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        # Try to extract numbers from expressions like "n days from now"
        num_days_match = re.search(r'(\d+) (ngày|days)', date_expr)
        if num_days_match:
            try:
                num_days = int(num_days_match.group(1))
                return (today + timedelta(days=num_days)).strftime('%Y-%m-%d')
            except ValueError:
                pass
                
        # Default to tomorrow if no matching pattern
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    
    def is_valid_date(self, date_str: str) -> bool:
        """
        Check if a date is valid and not in the past.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            True if the date is valid and not in the past
        """
        today = datetime.now().date()
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            return date_obj >= today
        except ValueError:
            return False
    
    def format_date_with_weekday(self, date_str: str, format: str = "%d/%m/%Y") -> str:
        """
        Format a date string with weekday name.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            format: Output date format
            
        Returns:
            Formatted date string with weekday (e.g., "Monday, 05/10/2025")
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            weekday_names = {
                0: "Thứ Hai",
                1: "Thứ Ba",
                2: "Thứ Tư", 
                3: "Thứ Năm",
                4: "Thứ Sáu",
                5: "Thứ Bảy",
                6: "Chủ Nhật"
            }
            weekday = weekday_names[date_obj.weekday()]
            return f"{weekday}, {date_obj.strftime(format)}"
        except ValueError:
            return date_str
