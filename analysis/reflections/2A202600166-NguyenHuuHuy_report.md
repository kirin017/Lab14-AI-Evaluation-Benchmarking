# BÁO CÁO ĐÁNH GIÁ HỆ THỐNG RAG (ROLE: DATA)
**Dự án:** Lab 14 - AI Evaluation Benchmarking  
**Vai trò:** Xử lý Data
**Ngày báo cáo:** 2026-04-21  
**MSSV:** 2A202600166  
**Họ Tên:** Nguyễn Hữu Huy
---

## 1. Đóng Góp Kỹ Thuật (Engineering Contribution)
Với vai trò **Data Role**, tôi đã trực tiếp thiết kế và triển khai các thành phần trọng yếu sau:
- **Module SDG (Synthetic Data Generation):** Xây dựng framework trong `synthetic_gen.py` sử dụng xử lý bất đồng bộ (`asyncio`) để tạo 74 test cases chất lượng cao từ dữ liệu thô chỉ trong chưa đầy 1 phút.
- **Hệ thống Metrics:** Code logic tính toán **Hit Rate** và **MRR** tự động sau mỗi lượt run benchmark, tích hợp trực tiếp vào pipeline đánh giá chung của nhóm.
- **Ground Truth Mapping:** Thiết kế cấu trúc dữ liệu mapping giữa câu hỏi và chính xác `chunk_id` chứa câu trả lời để đảm bảo việc đánh giá Retrieval là tuyệt đối chính xác (không dựa trên cảm tính của LLM).

## 2. Chiều Sâu Kỹ Thuật (Technical Depth)
Tôi xin giải trình các khái niệm cốt lõi đã áp dụng trong dự án:

- **MRR (Mean Reciprocal Rank):** Đây là metric quan trọng nhất để đánh giá Retrieval trong RAG. Nó không chỉ tính xem tài liệu đúng có nằm trong kết quả không (như Hit Rate) mà còn tính đến vị trí của nó. Nếu tài liệu đúng ở vị trí số 1, điểm là 1; vị trí số 2, điểm là 0.5. MRR trung bình cao chứng tỏ hệ thống của chúng tôi đưa thông tin chính xác lên đầu, giúp LLM giảm thiểu hiện tượng "Lost in the Middle".
- **Cohen's Kappa:** Trong hệ thống Multi-Judge, tôi sử dụng khái niệm này để đo lường độ đồng thuận giữa 2 Judge (GPT và Gemini) sau khi đã loại bỏ yếu tố ngẫu nhiên. Chỉ số đồng thuận 93% thực tế đã được kiểm chứng qua Kappa score cho thấy sự ổn định cực cao của Prompt Judge.
- **Position Bias:** Tôi đã nhận diện lỗi LLM Judge thường có xu hướng ưu tiên kết quả đứng trước hoặc có điểm số cao hơn nếu không có tiêu chí rõ ràng. Để khắc phục, tôi đã thiết kế Prompt Judge yêu cầu trích xuất bằng chứng (Evidence) trước khi cho điểm, buộc LLM phải "suy nghĩ" thay vì chọn theo thói quen vị trí.
- **Trade-off Chi phí & Chất lượng:** Thay vì dùng GPT-4o cho toàn bộ 74 cases (rất tốn kém), tôi sử dụng `gpt-4o-mini` và `gemini-3.1-flash-lite` làm Judge chính. Chỉ khi có xung đột (Conflict), hệ thống mới gọi đến `gpt-4o-mini-arbitrator`. Điều này giúp giảm 80% chi phí mà vẫn giữ được độ chính xác tương đương.

## 3. Giải Quyết Vấn Đề (Problem Solving)
Trong quá trình triển khai, tôi đã đối mặt và xử lý các vấn đề:
- **Vấn đề:** Khi sinh dữ liệu tổng hợp (SDG), LLM thường tạo ra các câu hỏi quá dễ hoặc lặp lại.
- **Giải pháp:** Tôi đã thêm bước "Diversity Check" và sử dụng `HARD_CASES_GUIDE.md` để ép LLM phải sinh các câu hỏi suy luận (Reasoning) thay vì chỉ trích xuất thông tin thuần túy.
- **Vấn đề:** Hệ thống Async bị lỗi Rate Limit khi chạy 2 Judge song song cho 74 cases.
- **Giải pháp:** Triển khai `asyncio.Semaphore(10)` để giới hạn số lượng request đồng thời, đảm bảo pipeline chạy mượt mà dưới 2 phút mà không bị lỗi API.
