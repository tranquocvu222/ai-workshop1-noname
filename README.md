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
- `/book` - Bắt đầu quy trình đặt lịch khám
- `/history` - Hiển thị lịch sử tương tác trước đó
- `/clear` - Xóa toàn bộ màn hình CLI
- `/save last` - Lưu đoạn hội thoại cuối cùng ra file text
- `/check slots` - Kiểm tra lịch trống của từng khoa
- `/my appointments` - Xem lịch khám cá nhân
- `/exit` - Thoát ứng dụng

## 🧩 Tính năng

1. **Đặt lịch thông minh**: Phân tích triệu chứng và gợi ý chuyên khoa phù hợp
2. **Tư vấn dựa trên triệu chứng**: Phân tích triệu chứng của bệnh nhân và đề xuất bác sĩ
3. **Kiểm tra lịch trống**: Xem khung giờ khám còn trống của từng khoa
4. **Quản lý lịch hẹn**: Thêm và xem lịch khám
5. **Trả lời câu hỏi**: Hỗ trợ giải đáp các thắc mắc liên quan đến phòng khám
6. **Phản hồi kiểu stream**: Hiển thị phản hồi AI từng ký tự một thay vì đợi toàn bộ phản hồi hoàn thành

## 🏥 Quy trình đặt lịch khám

1. Nhập `/book` hoặc trò chuyện tự nhiên với từ khóa "đặt lịch khám"
2. Nhập tên bệnh nhân
3. Mô tả triệu chứng
4. AI phân tích triệu chứng và gợi ý chuyên khoa phù hợp
5. Chọn khoa và bác sĩ
6. Chọn ngày và giờ khám từ các slot còn trống
7. Xác nhận đặt lịch

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
- Phản hồi được hiển thị theo kiểu stream, tạo trải nghiệm tương tác tự nhiên hơn
