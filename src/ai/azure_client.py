import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Callable, Generator
from dotenv import load_dotenv
import openai

class AzureOpenAIClient:
    """Client for interacting with Azure OpenAI API."""
    
    def __init__(self):
        """Initialize Azure OpenAI client with credentials from .env file."""
        load_dotenv()
        
        # Get Azure OpenAI credentials
        self.api_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME")
        
        # Load department and doctor data
        self.departments_data = self._load_departments_data()
        self.doctors_data = self._load_doctors_data()
        
        # Configure OpenAI client
        if self.api_endpoint and self.api_key:
            openai.api_type = "azure"
            openai.api_base = self.api_endpoint
            openai.api_key = self.api_key
            openai.api_version = "2023-05-15"  # Update with appropriate version
    
    def _load_departments_data(self) -> Dict:
        """Load department data from JSON file."""
        try:
            data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                    "data/departments.json")
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading departments data: {e}")
            return {"departments": []}
    
    def _load_doctors_data(self) -> Dict:
        """Load doctors data from JSON file."""
        try:
            data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                    "data/doctors.json")
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading doctors data: {e}")
            return {"doctors": []}
        
    def is_configured(self) -> bool:
        """Check if Azure OpenAI client is properly configured."""
        return all([self.api_endpoint, self.api_key, self.deployment_name])
    
    def generate_response(self, user_input: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generate a complete response using Azure OpenAI (non-streaming).
        
        Args:
            user_input: The user's query
            conversation_history: Optional list of previous conversation messages
            
        Returns:
            Generated response text
        """
        if not self.is_configured():
            return "⚠️ Azure OpenAI client is not properly configured. Please check your .env file."
        
        try:
            # Prepare conversation messages
            messages = conversation_history or []
            
            # Define system message with enhanced prompt engineering
            system_message = {
                "role": "system", 
                "content": f"""Bạn là trợ lý y tế thông minh tại phòng khám đa khoa, tên là Med Assistant.

NHIỆM VỤ CỦA BẠN:
1. Phân tích triệu chứng bệnh nhân và gợi ý chuyên khoa phù hợp
2. Trả lời câu hỏi về quy trình khám bệnh, chi phí và dịch vụ
3. Hướng dẫn đặt lịch khám bệnh
4. Giải thích các vấn đề y tế phổ biến một cách đơn giản, dễ hiểu

GIỌNG ĐIỆU:
- Chuyên nghiệp nhưng thân thiện
- Tôn trọng và đồng cảm với bệnh nhân
- Rõ ràng, ngắn gọn và dễ hiểu

GIỚI HẠN:
- Chỉ trả lời các câu hỏi liên quan đến y tế và dịch vụ phòng khám
- Không chẩn đoán bệnh chính xác, chỉ cung cấp thông tin chung và hướng dẫn
- Không tư vấn về thuốc hoặc liều lượng cụ thể
- Hướng dẫn bệnh nhân đến gặp bác sĩ với các tình trạng nghiêm trọng

THÔNG TIN BỔ SUNG:
- Hôm nay là ngày {datetime.now().strftime('%d/%m/%Y')}
- Phòng khám làm việc từ 8:00 - 17:00, từ thứ Hai đến thứ Bảy
"""
            }
            
            # Add system message if not already present
            if not messages or messages[0].get("role") != "system":
                messages = [system_message] + messages
            
            # Add user's new message
            messages.append({"role": "user", "content": user_input})
            
            # Call Azure OpenAI API
            response = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            # Extract assistant response
            return response.choices[0].message.content
            
        except Exception as e:
            return f"⚠️ Error generating response: {str(e)}"
    
    def generate_response_stream(self, user_input: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Generator[str, None, None]:
        """
        Generate a streaming response using Azure OpenAI.
        
        Args:
            user_input: The user's query
            conversation_history: Optional list of previous conversation messages
            
        Yields:
            Chunks of the generated response text as they become available
        """
        if not self.is_configured():
            yield "⚠️ Azure OpenAI client is not properly configured. Please check your .env file."
            return
        
        try:
            # Prepare conversation messages
            messages = conversation_history or []
            
            # Create doctor info string for the prompt
            doctor_info = ""
            for doc in self.doctors_data.get("doctors", []):
                doctor_info += f"- {doc.get('id', '')}: {doc.get('name', '')}, {doc.get('department_code', '')}, {doc.get('specialty', '')}, {doc.get('experience', '')}\n"
            
            # Create department info string
            department_info = ""
            for dept in self.departments_data.get("departments", []):
                dept_code = dept.get("code", "")
                department_info += f"- {dept_code}: {dept.get('name', '')}, {dept.get('description', '')}\n"
            
            # Check if user's query is specifically about doctors in a department
            department_keywords = [
                'nội tổng hợp', 'răng hàm mặt', 'tai mũi họng', 'mắt', 'da liễu', 'nhi khoa',
                'nội', 'răng', 'tai', 'mũi', 'họng', 'da', 'nhi'
            ]
            
            doctor_keywords = ['bác sĩ', 'doctor', 'bs']
            
            # Detect if this is a direct doctor query
            is_doctor_query = any(kw in user_input.lower() for kw in doctor_keywords) and any(kw in user_input.lower() for kw in department_keywords)
            
            system_message_content = f"""Bạn là trợ lý y tế thông minh tại phòng khám đa khoa, tên là Med Assistant.

NHIỆM VỤ CỦA BẠN:
1. Phân tích triệu chứng bệnh nhân và gợi ý chuyên khoa phù hợp
2. Trả lời câu hỏi về quy trình khám bệnh, chi phí và dịch vụ
3. Hướng dẫn đặt lịch khám bệnh
4. Giải thích các vấn đề y tế phổ biến một cách đơn giản, dễ hiểu

GIỌNG ĐIỆU:
- Chuyên nghiệp nhưng thân thiện
- Tôn trọng và đồng cảm với bệnh nhân
- Rõ ràng, ngắn gọn và dễ hiểu

GIỚI HẠN:
- Chỉ trả lời các câu hỏi liên quan đến y tế và dịch vụ phòng khám
- Không chẩn đoán bệnh chính xác, chỉ cung cấp thông tin chung và hướng dẫn
- Không tư vấn về thuốc hoặc liều lượng cụ thể
- Hướng dẫn bệnh nhân đến gặp bác sĩ với các tình trạng nghiêm trọng

THÔNG TIN BỔ SUNG:
- Hôm nay là ngày {datetime.now().strftime('%d/%m/%Y')}
- Phòng khám làm việc từ 8:00 - 17:00, từ thứ Hai đến thứ Bảy

DANH SÁCH CHUYÊN KHOA:
{department_info}

LƯU Ý QUAN TRỌNG:
- Khi người dùng hỏi về bác sĩ, hãy GỌI NGAY function getDoctor để lấy thông tin chính xác
- KHÔNG TRẢ LỜI CHUNG CHUNG khi được hỏi về bác sĩ cụ thể, mà phải gọi getDoctor
- Khi người dùng hỏi về bác sĩ của một khoa cụ thể (ví dụ: "Bác sĩ khoa Mắt là ai?"), luôn gọi getDoctor với department_code tương ứng
- LUÔN ưu tiên sử dụng function getDoctor thay vì trả lời rằng bạn không có thông tin
"""

            # Add special instruction for direct doctor queries
            if is_doctor_query:
                system_message_content += "\n\nĐÂY LÀ CÂU HỎI VỀ BÁC SĨ TRONG MỘT KHOA CỤ THỂ. HÃY GỌI FUNCTION getDoctor NGAY LẬP TỨC.\n"
            
            # Define system message
            system_message = {
                "role": "system", 
                "content": system_message_content
            }
            
            # Define functions for the model to call
            functions = [
                {
                    "name": "getDoctor",
                    "description": "Lấy thông tin bác sĩ theo các tiêu chí như mã khoa, chuyên khoa, ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "department_code": {
                                "type": "string",
                                "description": "Mã khoa (e.g., D01, D02, D03, D04, D05, D06, etc.)"
                            },
                            "doctor_id": {
                                "type": "string",
                                "description": "ID của bác sĩ (e.g., BS001, BS002, etc.)"
                            },
                            "specialty": {
                                "type": "string",
                                "description": "Chuyên khoa của bác sĩ (e.g., Nội khoa tổng quát, Tim mạch, etc.)"
                            }
                        },
                        "required": []
                    }
                }
            ]
            
            # Add system message if not already present
            if not messages or messages[0].get("role") != "system":
                messages = [system_message] + messages
            
            # Add user's new message
            messages.append({"role": "user", "content": user_input})
            
            # Set function call parameter based on query type
            function_call = "auto"
            if is_doctor_query:
                function_call = {"name": "getDoctor"}
            
            # Call Azure OpenAI API with function calling enabled
            response_stream = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                functions=functions,
                function_call=function_call,
                stream=True
            )
            
            # Variables to collect function calls and content
            collected_chunks = []
            collected_messages = ""
            function_call_detected = False
            function_name = None
            function_args = ""
            
            # Handle streaming response
            for chunk in response_stream:
                # Check if this chunk contains a function call
                if hasattr(chunk, "choices") and chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].get("delta", {})
                    
                    # Check if this is the start of a function call
                    if "function_call" in delta and delta["function_call"].get("name"):
                        function_call_detected = True
                        function_name = delta["function_call"]["name"]
                        yield f"Đang tìm kiếm thông tin bác sĩ... "
                    
                    # Collect function arguments if this is a function call
                    if function_call_detected and "function_call" in delta:
                        if "arguments" in delta["function_call"]:
                            function_args += delta["function_call"]["arguments"]
                    
                    # Otherwise handle normal content streaming
                    elif "content" in delta and delta["content"] is not None:
                        content = delta["content"]
                        collected_chunks.append(content)
                        collected_messages += content
                        yield content
            
            # If there was a function call, execute it and yield the result
            if function_call_detected and function_name == "getDoctor":
                try:
                    args = json.loads(function_args)
                    doctor_info = self.get_doctor(**args)
                    
                    # Format doctor information as a nicely formatted string
                    if isinstance(doctor_info, list) and doctor_info:
                        result = "Tôi đã tìm thấy các bác sĩ phù hợp:\n\n"
                        for doc in doctor_info:
                            result += f"- {doc.get('name', 'N/A')} ({doc.get('id', 'N/A')})\n"
                            result += f"  Chuyên khoa: {doc.get('specialty', 'N/A')}\n"
                            result += f"  Kinh nghiệm: {doc.get('experience', 'N/A')}\n"
                            result += f"  Học vấn: {doc.get('education', 'N/A')}\n\n"
                        yield f"\n\n{result}"
                    elif isinstance(doctor_info, dict):
                        doc = doctor_info
                        result = f"Tôi đã tìm thấy bác sĩ: {doc.get('name', 'N/A')} ({doc.get('id', 'N/A')})\n"
                        result += f"Chuyên khoa: {doc.get('specialty', 'N/A')}\n"
                        result += f"Kinh nghiệm: {doc.get('experience', 'N/A')}\n" 
                        result += f"Học vấn: {doc.get('education', 'N/A')}\n"
                        yield f"\n\n{result}"
                    else:
                        yield "\n\nKhông tìm thấy thông tin bác sĩ phù hợp với yêu cầu."
                except json.JSONDecodeError:
                    yield "\n\nCó lỗi xảy ra khi xử lý yêu cầu tìm kiếm bác sĩ."
            
            # Return full message if nothing was yielded (this should rarely happen)
            if not collected_chunks and not function_call_detected:
                yield ""
                
        except openai.error.APIError as e:
            yield "Hệ thống hiện đang gặp sự cố kết nối. Vui lòng thử lại sau ít phút."
        except openai.error.Timeout as e:
            yield "Hệ thống đang phản hồi chậm. Vui lòng thử lại sau."
        except openai.error.RateLimitError as e:
            yield "Hệ thống đang xử lý quá nhiều yêu cầu. Vui lòng thử lại sau ít phút."
        except openai.error.InvalidRequestError as e:
            yield "Yêu cầu không hợp lệ. Vui lòng thử lại với câu hỏi khác."
        except openai.error.AuthenticationError as e:
            yield "Hệ thống đang gặp vấn đề về xác thực. Vui lòng liên hệ quản trị viên."
        except Exception as e:
            yield f"Đã có lỗi xảy ra: {str(e)}. Vui lòng thử lại sau."
            
    def get_doctor(self, doctor_id: str = None, department_code: str = None, specialty: str = None) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
        """
        Get doctor information based on various search criteria.
        
        Args:
            doctor_id: Optional doctor ID to find a specific doctor
            department_code: Optional department code to filter doctors
            specialty: Optional specialty to filter doctors
            
        Returns:
            A doctor dict, list of doctor dicts, or None if no matches found
        """
        # Load all doctors data
        doctors = self.doctors_data.get("doctors", [])
        
        # If doctor_id is provided, find specific doctor
        if doctor_id:
            for doc in doctors:
                if doc.get("id") == doctor_id:
                    return doc
            return None
            
        # Filter doctors by criteria
        result = doctors
        
        # Filter by department_code if provided
        if department_code:
            result = [doc for doc in result if doc.get("department_code") == department_code]
            
        # Filter by specialty if provided (case-insensitive partial match)
        if specialty and specialty.strip():
            specialty = specialty.lower()
            result = [
                doc for doc in result 
                if doc.get("specialty") and specialty in doc.get("specialty", "").lower()
            ]
            
        # Return the filtered results (up to 5 doctors to avoid overwhelming responses)
        return result[:5] if result else None
            
    def analyze_symptoms(self, symptoms: str) -> Dict[str, Any]:
        """
        Analyze symptoms and suggest relevant departments and possible conditions.
        
        Args:
            symptoms: Description of symptoms
            
        Returns:
            Dictionary with analysis results including suggested departments and conditions
        """
        if not self.is_configured():
            return {"error": "Azure OpenAI client is not properly configured"}
        
        try:
            # Create department info for the prompt
            departments_info = ""
            for dept in self.departments_data.get("departments", []):
                departments_info += f"- {dept['code']}: {dept['name']} - {dept['description']}\n"
                
            # Create prompt for symptom analysis with department codes mapping and current date context
            today = datetime.now()
            prompt = f"""
# NHIỆM VỤ
Phân tích triệu chứng của bệnh nhân và đưa ra gợi ý về chuyên khoa phù hợp nhất để thăm khám.

# THÔNG TIN CHUNG
- Hôm nay là ngày {today.strftime('%d/%m/%Y')}
- Phòng khám đa khoa có các chuyên khoa sau:
{departments_info}

# YÊU CẦU PHÂN TÍCH
1. Xác định chuyên khoa phù hợp nhất dựa trên triệu chứng
2. Liệt kê các bệnh lý tiềm năng liên quan đến triệu chứng
3. Đánh giá mức độ nghiêm trọng của triệu chứng (Thấp/Trung bình/Cao)
4. Đề xuất lời khuyên ngắn gọn cho bệnh nhân

# TRIỆU CHỨNG CỦA BỆNH NHÂN
{symptoms}

# PHẢN HỒI
Hãy trả về kết quả phân tích dưới dạng JSON chính xác theo định dạng sau:
{{
    "department_codes": ["D01", "D03"],
    "departments": ["Nội tổng hợp", "Tai mũi họng"],
    "possible_conditions": ["Bệnh 1", "Bệnh 2"],
    "severity": "Mức độ nghiêm trọng",
    "recommendation": "Lời khuyên ngắn gọn"
}}
"""
            
            messages = [
                {"role": "system", "content": "Bạn là chuyên gia y tế, nhiệm vụ của bạn là phân tích triệu chứng và gợi ý chuyên khoa phù hợp. Luôn trả về kết quả dưới dạng JSON chính xác."},
                {"role": "user", "content": prompt}
            ]
            
            # Call Azure OpenAI API
            response = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=messages,
                max_tokens=800,
                temperature=0.2
            )
            
            # Extract and parse JSON response
            response_text = response.choices[0].message.content
            
            # Find JSON content within the response (in case there's additional text)
            json_match = re.search(r'({[\s\S]*})', response_text)
            if json_match:
                response_text = json_match.group(1)
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {
                    "error": "Failed to parse response",
                    "raw_response": response_text
                }
                
        except openai.error.APIError:
            return {"error": "Hệ thống hiện đang gặp sự cố kết nối. Vui lòng thử lại sau ít phút."}
        except openai.error.Timeout:
            return {"error": "Hệ thống đang phản hồi chậm. Vui lòng thử lại sau."}
        except openai.error.RateLimitError:
            return {"error": "Hệ thống đang xử lý quá nhiều yêu cầu. Vui lòng thử lại sau ít phút."}
        except openai.error.InvalidRequestError:
            return {"error": "Yêu cầu không hợp lệ. Vui lòng thử lại với mô tả triệu chứng khác."}
        except openai.error.AuthenticationError:
            return {"error": "Hệ thống đang gặp vấn đề về xác thực. Vui lòng liên hệ quản trị viên."}
        except Exception as e:
            return {"error": "Đã có lỗi xảy ra. Vui lòng thử lại sau."}
    
    def get_doctor_suggestions(self, department_code: str) -> List[Dict[str, str]]:
        """
        Get suggested doctors for a specific department.
        
        Args:
            department_code: Department code (e.g., 'D01')
            
        Returns:
            List of doctor information dictionaries
        """
        # Use the new get_doctor function
        doctors = self.get_doctor(department_code=department_code)
        if doctors:
            return doctors
            
        # If no doctors found, fall back to AI generation
        try:
            # Get department name
            dept_name = "Unknown"
            for dept in self.departments_data.get("departments", []):
                if dept.get("code") == department_code:
                    dept_name = dept.get("name")
                    break
            
            prompt = f"""
# NHIỆM VỤ
Gợi ý 3 bác sĩ làm việc tại khoa {dept_name} (mã khoa: {department_code}).

# YÊU CẦU
1. Check thời gian trống
2. Thông tin phải thực tế, phù hợp với chuyên khoa
4. Cung cấp thông tin về chuyên môn và kinh nghiệm

# PHẢN HỒI
Trả về kết quả dưới dạng JSON chính xác với định dạng sau:
{{
    "doctors": [
        {{"id": "BS001", "name": "Tên Bác Sĩ", "department_code": "{department_code}", "specialty": "Chuyên khoa", "experience": "Số năm kinh nghiệm", "education": "Trường đào tạo"}},
        {{"id": "BS002", "name": "Tên Bác Sĩ", "department_code": "{department_code}", "specialty": "Chuyên khoa", "experience": "Số năm kinh nghiệm", "education": "Trường đào tạo"}},
        {{"id": "BS003", "name": "Tên Bác Sĩ", "department_code": "{department_code}", "specialty": "Chuyên khoa", "experience": "Số năm kinh nghiệm", "education": "Trường đào tạo"}}
    ]
}}
"""
            
            messages = [
                {"role": "system", "content": "Bạn là trợ lý y tế, nhiệm vụ của bạn là cung cấp thông tin về bác sĩ theo chuyên khoa. Luôn trả về kết quả dưới dạng JSON chính xác."},
                {"role": "user", "content": prompt}
            ]
            
            # Call Azure OpenAI API
            response = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=messages,
                max_tokens=600,
                temperature=0.5
            )
            
            # Extract and parse JSON response
            response_text = response.choices[0].message.content
            
            # Find JSON content within the response
            json_match = re.search(r'({[\s\S]*})', response_text)
            if json_match:
                response_text = json_match.group(1)
            
            try:
                result = json.loads(response_text)
                return result.get("doctors", [])
            except json.JSONDecodeError:
                return [{"error": "Failed to parse doctor suggestions"}]
                
        except openai.error.APIError:
            return [{"error": "Hệ thống hiện đang gặp sự cố kết nối. Vui lòng thử lại sau ít phút."}]
        except openai.error.Timeout:
            return [{"error": "Hệ thống đang phản hồi chậm. Vui lòng thử lại sau."}]
        except openai.error.RateLimitError:
            return [{"error": "Hệ thống đang xử lý quá nhiều yêu cầu. Vui lòng thử lại sau ít phút."}]
        except openai.error.InvalidRequestError:
            return [{"error": "Yêu cầu không hợp lệ. Vui lòng thử lại."}]
        except openai.error.AuthenticationError:
            return [{"error": "Hệ thống đang gặp vấn đề về xác thực. Vui lòng liên hệ quản trị viên."}]
        except Exception as e:
            return [{"error": "Đã có lỗi xảy ra. Vui lòng thử lại sau."}]
