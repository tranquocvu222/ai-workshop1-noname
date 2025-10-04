
# 🏥 Medical Assistant CLI – Design Document

## 🧠 Overview
Ứng dụng CLI hỗ trợ phòng khám trong việc tra cứu và quản lý lịch khám bệnh.  
Dữ liệu được lưu trữ cục bộ trong file JSON và tích hợp **Azure OpenAI** để sinh phản hồi tự nhiên (ví dụ: tư vấn, xác nhận lịch khám, tạo email, v.v.).

---

## ⚙️ Tech Stack
- **Language:** Python 3.10+
- **Platform:** macOS / Linux
- **AI Provider:** Azure OpenAI
- **Data Storage:** Local JSON file (`data/appointments.json`)
- **Environment Config:** `.env` file (Azure keys, endpoint, deployment name)

---

## 🧩 Features

### 1. Azure OpenAI Integration
Ứng dụng sử dụng **Azure OpenAI** để sinh phản hồi tự nhiên cho người dùng.  
Không lưu trữ code liên quan đến API trong repo, chỉ mô tả cơ chế sử dụng.

**Cấu hình thông qua file `.env`:**
```env
AZURE_OPENAI_ENDPOINT=<your_azure_endpoint>
AZURE_OPENAI_API_KEY=<your_api_key>
AZURE_DEPLOYMENT_NAME=<your_deployment_name>
````

---

### 2. Appointment Management (Local JSON)

Tất cả lịch khám của phòng khám được lưu trong file `data/appointments.json`.

**Ví dụ file JSON:**

```json
{
  "appointments": [
    {
      "department": "Nội tổng hợp",
      "doctor": "BS. Nguyễn Văn A",
      "date": "2025-10-05",
      "time": "09:00",
      "patient": "Nguyễn Thị B"
    },
    {
      "department": "Răng hàm mặt",
      "doctor": "BS. Lê Thị B",
      "date": "2025-10-05",
      "time": "10:00",
      "patient": "Nguyễn Thị C"
    }
  ]
}
```

---

### 3. Available Slot Checking

Ứng dụng có khả năng:

🧩 1. Requirement ban đầu (Initial Requirements)
🎯 Mục tiêu chính của hệ thống:
 • Tiếp nhận thông tin từ bệnh nhân (triệu chứng, câu hỏi).
 • Phân tích thông tin để xác định bệnh lý tiềm năng.
 • Tư vấn chuyên khoa phù hợp để khám và điều trị.
 • Trả lời các câu hỏi phổ biến liên quan đến bệnh, quy trình khám, chi phí, v.v.
📥 Input từ người dùng:
 • Văn bản mô tả triệu chứng (ví dụ: “Tôi bị đau đầu, chóng mặt, buồn nôn”).
 • Câu hỏi cụ thể (ví dụ: “Tôi nên khám ở khoa nào?”, “Đây có phải dấu hiệu của bệnh gì không?”).
📤 Output từ hệ thống:
 • Phân tích sơ bộ triệu chứng.
 • Gợi ý bệnh lý tiềm năng (nếu có).
 • Gợi ý chuyên khoa phù hợp (ví dụ: Nội thần kinh, Tiêu hóa, Tai mũi họng…).
 • Trả lời các câu hỏi liên quan đến bệnh và quy trình khám.

🔍 2. Cải thiện Requirement (Chi tiết hơn)
🧠 Các chức năng chính của Chatbox:
 1. Phân tích triệu chứng: Dùng NLP để hiểu và phân loại triệu chứng.
 2. Gợi ý chuyên khoa: Mapping triệu chứng → chuyên khoa.
 3. Tư vấn bệnh lý: Dựa trên triệu chứng phổ biến, gợi ý bệnh lý tiềm năng.
 4. Trả lời câu hỏi: FAQ hoặc AI trả lời theo ngữ cảnh.
 5. Chuyển tiếp đến bác sĩ thật (nếu cần): Nếu triệu chứng phức tạp, chuyển tiếp đến nhân viên y tế.

**Ví dụ output trong terminal:**

```
📅 Date: 2025-10-05

🩺 Khoa Nội tổng hợp:
  ✅ Available: 08:00, 10:00, 14:00, 15:30

🦷 Khoa Răng hàm mặt:
  ✅ Available: 08:00, 09:00, 11:00, 14:30
```

---

### 4. Master Data (Departments)

| Mã khoa | Tên khoa     | Mô tả chi tiết                                 |
| ------- | ------------ | ---------------------------------------------- |
| D01     | Nội tổng hợp | Khám tổng quát, điều trị các bệnh thông thường |
| D02     | Răng hàm mặt | Chăm sóc răng miệng, chỉnh nha, tiểu phẫu      |
| D03     | Tai mũi họng | Khám, điều trị các bệnh lý về tai, mũi, họng   |
| D04     | Mắt          | Khám thị lực, điều trị cận thị, loạn thị       |
| D05     | Da liễu      | Điều trị mụn, viêm da, dị ứng, lão hóa         |
| D06     | Nhi khoa     | Khám trẻ em, tư vấn dinh dưỡng, tiêm chủng     |

---

### 5. CLI Pro Mode

CLI được thiết kế có màu sắc hiển thị (sử dụng thư viện `rich`)
và hỗ trợ các lệnh mở rộng:

| Command        | Description                               |
| -------------- | ----------------------------------------- |
| `/history`     | Hiển thị lịch sử tương tác trước đó       |
| `/clear`       | Xóa toàn bộ màn hình CLI                  |
| `/save last`   | Lưu đoạn hội thoại cuối cùng ra file text |
| `/check slots` | Kiểm tra lịch trống của từng khoa         |
| `/help`        | Hiển thị danh sách lệnh khả dụng          |

---

### 6. CLI Example Interaction

**User:**

> Hi, show available slots for tomorrow in “Răng hàm mặt”.

**System:**

```
🦷 Department: Răng hàm mặt
📅 Date: 2025-10-06
✅ Available: 08:00, 09:30, 11:00, 14:00
```

---

7. Example of Irrelevant Question

- User:
```
What’s the weather today?
```

-System:
```
🤖 Xin lỗi, tôi chỉ có thể hỗ trợ bạn trong các vấn đề liên quan đến phòng khám và đặt lịch khám bệnh.
```

## 🗂 Project Structure

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
│       └── azure_client.py        # Azure OpenAI integration (mô tả)
│
├── .env                           # Azure credentials
├── requirements.txt
└── README.md
```

---

## 📦 Requirements

```text
# requirements.txt
python-dotenv
openai
rich
typer
```

---

## 🚀 Run Project

```bash
# 1️⃣ Tạo môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# 2️⃣ Cài đặt dependencies
pip install -r requirements.txt

# 3️⃣ Chạy ứng dụng
python src/main.py
```

---

## 💬 Notes

* Ứng dụng chỉ **sử dụng Azure OpenAI** cho việc sinh ngôn ngữ tự nhiên.
* Không lưu hoặc gửi dữ liệu cá nhân ra ngoài.
* Dữ liệu lịch khám được quản lý **cục bộ (offline)**.
* Có thể mở rộng thêm: đồng bộ Google Calendar, gửi email xác nhận, API REST cho web dashboard, v.v.



