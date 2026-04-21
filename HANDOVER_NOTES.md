# 📘 AI Evaluation Factory - Handover & Results

Tài liệu này tổng hợp kết quả Benchmark hiện tại và hướng dẫn dành cho thành viên tiếp theo hoặc người chấm bài.

## 📊 Kết quả Benchmark hiện tại (21/04/2026)

Hệ thống đã chạy thành công trên **74 test cases** (bao gồm 20 Hard Cases) với **Agent thực tế (RAG)**.

| Chỉ số | Giá trị | Nhận xét |
|:--- |:--- |:--- |
| **Model sử dụng** | GPT-4o-mini & Gemini 3.1 Flash-Lite | Đáp ứng yêu cầu ít nhất 2 model khác nhau. |
| **Average Score** | **4.18 / 5.0** | Hiệu năng rất tốt với Agent RAG thực tế. |
| **Agreement Rate**| **93% (Very High)** | Độ tin cậy cực cao, các Judge đồng thuận trên hầu hết các case. |
| **Pass Rate** | **~85%** | Đa số các case đạt điểm >= 3.0. |

> [!IMPORTANT]
> **Hard Cases Analysis:** Agent vẫn gặp lỗi ở các case tấn công giả mạo (Prompt Injection) và các câu hỏi suy luận chéo tài liệu (Multi-doc). Đây là các điểm cần tập trung cải thiện Prompt cho Agent.

> [!TIP]
> **Judge Alignment:** GPT-4o-mini và Gemini 3.1 Flash-Lite hiện tại có độ đồng thuận rất cao (93%). Cả hai đều cho thấy khả năng nhận diện chính xác các lỗi về logic và bảo mật trong các Hard Cases.

---

## 🚀 Hướng dẫn sử dụng cho người tiếp theo

### 1. Chuẩn bị môi trường
Đảm bảo đã cài đặt đầy đủ dependencies và cấu hình API Key:
```bash
pip install -r requirements.txt
# Đảm bảo file .env có OPENAI_API_KEY và GEMINI_API_KEY hợp lệ
```

### 2. Thay thế Agent thực tế
Để đánh giá Agent của bạn, hãy cập nhật logic tại:
👉 `agent/main_agent.py` -> Sửa hàm `query()` để gọi đến Agent thực (RAG pipeline).

### 3. Chạy Benchmark
Sau khi thay đổi Agent hoặc bộ dữ liệu, chạy lệnh sau:
```bash
# 1. Tạo bộ dữ liệu (nếu cần)
python data/synthetic_gen.py

# 2. Chạy đánh giá
python main.py
```

### 4. Xem kết quả
Kết quả chi tiết và tổng quát sẽ tự động cập nhật tại:
- `reports/summary.json`: Tổng hợp các chỉ số chất lượng, độ tin cậy.
- `reports/benchmark_results.json`: Chi tiết lý do (reasoning) của từng model cho từng case.

---

## 🛠️ Cấu hình Consensus Engine
Hệ thống xử lý xung đột tự động theo chiến lược `median_then_arbitrator`:
1. Nếu 2 model lệch nhau $\le 1.0$: Lấy trung bình cộng.
2. Nếu lệch $> 1.0$: Gọi thêm **Arbitrator (Trọng tài)** và lấy trung vị (Median) của cả 3.

*Chúc nhóm hoàn thiện bài lab với điểm số tuyệt đối!*
