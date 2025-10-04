import os
import json
from typing import Dict, List, Optional, Union, Any
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
        Generate a response using Azure OpenAI.
        
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
            # Create prompt for symptom analysis
            prompt = f"""
            Phân tích các triệu chứng sau và cung cấp thông tin về:
            1. Chuyên khoa phù hợp để thăm khám (từ danh sách: Nội tổng hợp, Răng hàm mặt, Tai mũi họng, Mắt, Da liễu, Nhi khoa)
            2. Các bệnh lý tiềm năng liên quan đến triệu chứng
            3. Mức độ nghiêm trọng (Thấp/Trung bình/Cao)
            
            Triệu chứng: {symptoms}
            
            Trả về kết quả dưới dạng JSON với định dạng sau:
            {{
                "departments": ["Tên khoa 1", "Tên khoa 2"],
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
            import re
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
                
        except Exception as e:
            return {"error": f"Error analyzing symptoms: {str(e)}"}
