# Phản hồi Cá nhân — Nhóm AI/Backend (Consensus Engine)

## 1. Engineering Contribution (Đóng góp Kỹ thuật)

Tôi chịu trách nhiệm chính trong việc thiết kế và triển khai **Multi-Judge Consensus Engine**, module hạt nhân đảm bảo tính khách quan cho toàn bộ hệ thống đánh giá.

*   **Kiến trúc Async**: Toàn bộ luồng đánh giá được tối ưu hóa bằng `asyncio`. Tôi đã triển khai cơ chế gọi song song các Judge (OpenAI và Google) qua `asyncio.gather()`, giúp giảm thời gian thực thi tổng thể hơn 60%, đáp ứng tiêu chí hiệu năng cao của Lab.
*   **Thuật toán Consensus & Calibration**:
    - Thiết kế hệ số **Agreement Rate** linh hoạt, không chỉ dựa trên việc so khớp điểm số mà còn kết hợp trọng số `Variance Smoothing` (70% pairwise + 30% variance smoothness) để giảm nhiễu từ các Judge có sự biến động lớn.
    - Triển khai nhãn **Agreement Level** (`Very High`, `High`, `Moderate`, `Low`) giúp người dùng cuối dễ dàng nhận diện độ tin cậy của kết quả mà không cần phân tích số liệu thô.
*   **Xử lý Xung đột Tự động**: Xây dựng logic xử lý 3 tầng:
    - **Tầng 1 (Mean)**: Khi độ lệch giữa các Judge $\le 1.0$ (Mức độ đồng thuận cao).
    - **Tầng 2 (Median)**: Khi độ lệch trong khoảng (1.0 - 2.0] (Mức độ đồng thuận trung bình, dùng trung vị để loại bỏ outlier).
    - **Tầng 3 (Arbitrator Median)**: Khi xung đột nghiêm trọng ($> 2.0$), hệ thống tự động gọi Arbitrator (GPT-4o-mini-arb) và lấy điểm trung vị của cả 3 kết quả để chốt điểm số cuối cùng.

## 2. Technical Depth (Chiều sâu Kỹ thuật)

Trong quá trình thực hiện, tôi đã nghiên cứu và làm rõ các khái niệm chuyên sâu về AI Evaluation:

*   **MRR (Mean Reciprocal Rank)**: Tôi đã tích hợp MRR vào chỉ số thành phần để đánh giá khả năng "xếp hạng" của Retriever. MRR giúp đo lường xem thông tin Ground Truth nằm ở vị trí thứ mấy trong Top-K kết quả. Kết quả đạt được là **0.75**, chứng minh Retriever (với embedding hash) hoạt động khá hiệu quả khi trả về tài liệu đúng ở rank 1 hoặc 2.
*   **Cohen's Kappa & Inter-rater Reliability**: Tôi đã phân tích trade-off giữa việc dùng tỷ lệ đồng thuận thô (Agreement Rate) và hệ số Kappa. Tôi nhận ra rằng với hệ thống chấm điểm liên tục (Ordinal Scale), việc dùng thống kê Variance (phương sai) trong Calibration sẽ hiệu quả hơn việc dùng Kappa khi số lượng Judge ít (2-3 Judge).
*   **Position Bias**: Nhận diện hiện tượng Judge LLM thích thông tin ở đầu hoặc cuối context (Primacy/Recency Bias). Tôi đã thiết kế Prompt cho Judge để ép model tập trung vào logic thay vì hình thức trình bày, đồng thời theo dõi "Bias score" của từng model Judge qua chỉ số `judge_reliability`.
*   **Trade-off Chi phí và Chất lượng**: Tôi đã giải trình được hiệu quả của việc dùng **"Consensus of Minis"** (Sự đồng thuận của các model nhỏ). Thay vì tốn phí cho 1 model lớn (GPT-4o), việc dùng 2 model nhỏ (GPT-4o-mini & Gemini Flash) kết hợp với logic Consensus mang lại điểm số có độ tin cậy cao hơn (~93% agreement) với chi phí rẻ hơn 10-15 lần.

## 3. Problem Solving (Giải quyết Vấn đề)

*   **Xử lý lỗi Provider**: Gặp lỗi 404/Not Found khi gọi Gemini qua OpenAI-compatible SDK (2026). Tôi đã tự viết script chẩn đoán (`list_models.py`) để tìm ra model identifier đúng là `gemini-flash-lite-latest` và cấu hình lại base URL thành `v1beta/openai/`.
*   **Cân chỉnh dữ liệu Hard Cases**: Khi chạy các case Red-teaming (Prompt Injection), tôi nhận thấy Judge có xu hướng chấm điểm thấp cho Agent dù Agent đã từ chối yêu cầu sai trái một cách đúng đắn. Tôi đã điều chỉnh lại Rubric chấm điểm trong `llm_judge.py` để ghi nhận các phản hồi "An toàn" (Security-aware) là câu trả lời đúng (Accuracy=5).
*   **Vulnerability in Hash Embeddings**: Phát hiện giới hạn của Hash-based embedding trong việc hiểu ngữ nghĩa (kém hơn semantic embedding). Để giải quyết mà không tăng chi phí, tôi đã triển khai kỹ thuật **Hybrid Batching** trong runner để đảm bảo tính ổn định của hệ thống khi khối lượng test case lớn.
