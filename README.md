# 🏥 Medical Assistant CLI

Ứng dụng CLI hỗ trợ phòng khám trong việc tra cứu và quản lý lịch khám bệnh. Dữ liệu được lưu trữ cục bộ trong file JSON và tích hợp **Azure OpenAI** để sinh phản hồi tự nhiên (ví dụ: tư vấn, xác nhận lịch khám, tạo email, v.v.).

## ⚙️ Cài đặt

1. Clone repository này
2. Tạo file `.env` với các thông tin Azure OpenAI của bạn:

```
AZURE_OPENAI_ENDPOINT=<your_azure_endpoint>
AZURE_OPENAI_API_KEY=<your_api_key>
AZURE_DEPLOYMENT_NAME=<your_deployment_name>
```

3. Cài đặt dependencies:

```bash
# Tạo môi trường ảo
python3 -m venv .venv
source .venv/bin/activate  # Trên Windows: .venv\Scripts\activate

# Cài đặt dependencies
pip install -r requirements.txt
```

## 🚀 Sử dụng

Chạy ứng dụng:

```bash
python src/main.py
```

### Các lệnh có sẵn:

- `/help` - Hiển thị danh sách lệnh khả dụng
- `/history` - Hiển thị lịch sử tương tác trước đó
- `/clear` - Xóa toàn bộ màn hình CLI
- `/save last` - Lưu đoạn hội thoại cuối cùng ra file text
- `/check slots` - Kiểm tra lịch trống của từng khoa
- `/exit` - Thoát ứng dụng

## 🧩 Tính năng

1. **Tư vấn dựa trên triệu chứng**: Phân tích triệu chứng của bệnh nhân và gợi ý khoa phù hợp
2. **Kiểm tra lịch trống**: Xem khung giờ khám còn trống của từng khoa
3. **Trả lời câu hỏi**: Hỗ trợ giải đáp các thắc mắc liên quan đến phòng khám

## 🗂 Cấu trúc dự án

```
medical-assistant/
│
├── data/
│   └── appointments.json          # Lưu lịch khám
│
├── src/
│   ├── main.py                    # CLI chính
│   ├── utils/
│   │   └── scheduler.py           # Đọc JSON, check khung giờ trống
│   └── ai/
│       └── azure_client.py        # Azure OpenAI integration
│
├── .env                           # Azure credentials
├── requirements.txt
└── README.md
```

## 📝 Ghi chú

- Ứng dụng chỉ **sử dụng Azure OpenAI** cho việc sinh ngôn ngữ tự nhiên
- Dữ liệu lịch khám được quản lý **cục bộ (offline)**
- Không lưu hoặc gửi dữ liệu cá nhân ra ngoài
