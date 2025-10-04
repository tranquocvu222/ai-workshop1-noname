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
        
        # Configure OpenAI client
        if self.api_endpoint and self.api_key:
            openai.api_type = "azure"
            openai.api_base = self.api_endpoint
            openai.api_key = self.api_key
            openai.api_version = "2023-05-15"  # Update with appropriate version
        
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
            
            # Define system message for medical assistant behavior
            system_message = {
                "role": "system", 
                "content": """Bạn là trợ lý ảo của phòng khám đa khoa. 
                Nhiệm vụ của bạn là phân tích triệu chứng, tư vấn chuyên khoa phù hợp, 
                và trả lời các câu hỏi liên quan đến quy trình khám bệnh. 
                Giọng điệu thân thiện, chuyên nghiệp. 
                Chỉ trả lời các câu hỏi liên quan đến y tế và dịch vụ phòng khám.
                Không trả lời các câu hỏi không liên quan.
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
            
            # Define system message for medical assistant behavior
            system_message = {
                "role": "system", 
                "content": f"""Bạn là trợ lý ảo của phòng khám đa khoa. 
                Nhiệm vụ của bạn là phân tích triệu chứng, tư vấn chuyên khoa phù hợp, 
                và trả lời các câu hỏi liên quan đến quy trình khám bệnh. 
                Giọng điệu thân thiện, chuyên nghiệp. 
                Chỉ trả lời các câu hỏi liên quan đến y tế và dịch vụ phòng khám.
                Không trả lời các câu hỏi không liên quan.
                
                Hôm nay là ngày {datetime.now().strftime('%d/%m/%Y')}.
                """
            }
            
            # Add system message if not already present
            if not messages or messages[0].get("role") != "system":
                messages = [system_message] + messages
            
            # Add user's new message
            messages.append({"role": "user", "content": user_input})
            
            # Call Azure OpenAI API with streaming enabled
            response_stream = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                stream=True
            )
            
            # Yield chunks as they arrive
            collected_chunks = []
            collected_messages = ""
            
            for chunk in response_stream:
                # Extract content from chunk if available
                if hasattr(chunk, "choices") and chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].get("delta", {}).get("content")
                    if content is not None:
                        collected_chunks.append(content)
                        collected_messages += content
                        yield content
            
            # Return full message if nothing was yielded (this should rarely happen)
            if not collected_chunks:
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
            yield "Đã có lỗi xảy ra. Vui lòng thử lại sau. Nếu vấn đề còn tiếp tục, hãy liên hệ quản trị viên."
            
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
            # Create prompt for symptom analysis with department codes mapping and current date context
            today = datetime.now()
            prompt = f"""
            Hôm nay là ngày {today.strftime('%d/%m/%Y')}.
            
            Phân tích các triệu chứng sau và cung cấp thông tin về:
            1. Chuyên khoa phù hợp để thăm khám. Dựa trên danh sách sau:
               - D01: Nội tổng hợp - Khám tổng quát, điều trị các bệnh thông thường
               - D02: Răng hàm mặt - Chăm sóc răng miệng, chỉnh nha, tiểu phẫu
               - D03: Tai mũi họng - Khám, điều trị các bệnh lý về tai, mũi, họng
               - D04: Mắt - Khám thị lực, điều trị cận thị, loạn thị
               - D05: Da liễu - Điều trị mụn, viêm da, dị ứng, lão hóa
               - D06: Nhi khoa - Khám trẻ em, tư vấn dinh dưỡng, tiêm chủng
            
            2. Các bệnh lý tiềm năng liên quan đến triệu chứng
            3. Mức độ nghiêm trọng (Thấp/Trung bình/Cao)
            
            Triệu chứng: {symptoms}
            
            Trả về kết quả dưới dạng JSON với định dạng sau:
            {{
                "department_codes": ["D01", "D03"], // Mã khoa phù hợp
                "departments": ["Nội tổng hợp", "Tai mũi họng"], // Tên khoa phù hợp
                "possible_conditions": ["Bệnh 1", "Bệnh 2"],
                "severity": "Mức độ",
                "recommendation": "Lời khuyên ngắn gọn"
            }}
            """
            
            messages = [
                {"role": "system", "content": "Bạn là trợ lý y tế, chuyên phân tích triệu chứng và đưa ra gợi ý chuyên môn."},
                {"role": "user", "content": prompt}
            ]
            
            # Call Azure OpenAI API
            response = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=messages,
                max_tokens=500,
                temperature=0.3
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
        if not self.is_configured():
            return [{"error": "Azure OpenAI client is not properly configured"}]
        
        try:
            dept_names = {
                "D01": "Nội tổng hợp",
                "D02": "Răng hàm mặt",
                "D03": "Tai mũi họng",
                "D04": "Mắt",
                "D05": "Da liễu",
                "D06": "Nhi khoa"
            }
            
            dept_name = dept_names.get(department_code, "Unknown")
            
            prompt = f"""
            Gợi ý 3 bác sĩ làm việc tại khoa {dept_name} ({department_code}).
            
            Trả về kết quả dưới dạng JSON với định dạng sau:
            {{
                "doctors": [
                    {{"id": "BS001", "name": "Tên Bác Sĩ", "specialty": "Chuyên khoa", "experience": "Số năm kinh nghiệm"}},
                    {{"id": "BS002", "name": "Tên Bác Sĩ", "specialty": "Chuyên khoa", "experience": "Số năm kinh nghiệm"}},
                    {{"id": "BS003", "name": "Tên Bác Sĩ", "specialty": "Chuyên khoa", "experience": "Số năm kinh nghiệm"}}
                ]
            }}
            
            Tất cả thông tin cần hợp lý và chuyên nghiệp. Tên bác sĩ phải là tên Việt Nam.
            """
            
            messages = [
                {"role": "system", "content": "Bạn là trợ lý y tế, chuyên cung cấp thông tin về bác sĩ."},
                {"role": "user", "content": prompt}
            ]
            
            # Call Azure OpenAI API
            response = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=messages,
                max_tokens=500,
                temperature=0.7
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
