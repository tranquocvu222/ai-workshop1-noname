import json
import os
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Set, Tuple

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
    
    def add_appointment(self, department: str, doctor: str, date: str, time: str, patient: str) -> bool:
        """
        Add a new appointment to the schedule.
        
        Args:
            department: Department name
            doctor: Doctor name
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            patient: Patient name
            
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
            "patient": patient
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
