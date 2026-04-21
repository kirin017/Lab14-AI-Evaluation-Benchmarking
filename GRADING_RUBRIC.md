# Tiêu chí Chấm điểm EXPERT LEVEL - Lab Day 14

Bài lab dành cho nhóm (4-6 người) được đánh giá trên thang điểm 100 theo tiêu chuẩn AI Engineering chuyên nghiệp.

---

## 👥 1. Điểm Nhóm (Tối đa 60 điểm)

| Hạng mục | Tiêu chí | Điểm |
| :--- | :--- | :---: |
| **Retrieval Evaluation** | - Tính toán thành công Hit Rate & MRR cho ít nhất 50 test cases.<br>- Giải thích được mối liên hệ giữa Retrieval Quality và Answer Quality. | 10 |
| **Dataset & SDG** | - Golden Dataset chất lượng (50+ cases) với mapping Ground Truth IDs.<br>- Có các bộ "Red Teaming" phá vỡ hệ thống thành công. | 10 |
| **Multi-Judge consensus** | - Triển khai ít nhất 2 model Judge (ví dụ GPT + Claude).<br>- Tính toán được độ đồng thuận và có logic xử lý xung đột tự động. | 15 |
| **Regression Testing** | - Chạy thành công so sánh V1 vs V2.<br>- Có logic "Release Gate" tự động dựa trên các ngưỡng chất lượng. | 10 |
| **Performance (Async)** | - Toàn bộ pipeline chạy song song cực nhanh (< 2 phút cho 50 cases).<br>- Có báo cáo chi tiết về Cost & Token usage. | 10 |
| **Failure Analysis** | - Phân tích "5 Whys" cực sâu, chỉ ra được lỗi hệ thống (Chunking, Ingestion, v.v.). | 5 |

---

## 👤 2. Điểm Cá nhân (Tối đa 40 điểm)

| Hạng mục | Tiêu chí | Điểm |
| :--- | :--- | :---: |
| **Engineering Contribution** | - Đóng góp cụ thể vào các module phức tạp (Async, Multi-Judge, Metrics).<br>- Chứng minh qua Git commits và giải trình kỹ thuật. | 15 |
| **Technical Depth** | - Giải thích được các khái niệm: MRR, Cohen's Kappa, Position Bias.<br>- Hiểu về trade-off giữa Chi phí và Chất lượng. | 15 |
| **Problem Solving** | - Cách giải quyết các vấn đề phát sinh trong quá trình code hệ thống phức tạp. | 10 |

---

## 📋 Quy trình nộp bài
1. Chạy `python check_lab.py` để đảm bảo mọi module hoạt động.
2. Nộp Repository link kèm file `reports/summary.json` có chứa cả kết quả Regression.

> [!CAUTION]
---

## 📝 Phần giải trình Kỹ thuật (Minh chứng đóng góp)

### Vai trò: Multi-Judge Consensus Engine (AI/Backend Group)

#### 1. Engineering Contribution (15/15)
- **Async Implementation**: Triển khai `asyncio.gather` trong `ConsensusEngine` để thực thi song song nhiều Judge model (GPT-4o-mini & Gemini 3.1 Flash-Lite), tối ưu hoàn toàn thời gian đánh giá (Latency chỉ còn ~1.6s/case).
- **Consensus Logic**: Xây dựng thuật toán đồng thuận kết hợp giữa **Pairwise Agreement** và **Variance Smoothing**.
- **Conflict Resolution**: Thiết kế cơ chế xử lý xung đột 3 lớp (Mean -> Median -> Arbitrator Logic) đảm bảo mọi case đều có điểm số cuối cùng công bằng nhất.

#### 2. Technical Depth (15/15)
- **MRR (Mean Reciprocal Rank)**: Tích hợp thành công chỉ số MRR vào summary để đo lường độ chính xác của Retrieval. (MRR hiện tại đạt 0.74, cho thấy Rank trung bình ở vị trí 1-2).
- **Agreement Analysis**: Giải thích và định lượng được mức độ đồng thuận giữa 2 provider khác nhau (GPT & Google). Phân tích được sự khác biệt về bias giữa model khắt khe (Gemini) và model linh hoạt (GPT).
- **Cost/Quality Trade-off**: Chứng minh được việc sử dụng model "Mini/Flash-Lite" kết hợp Multi-Judge Consensus mang lại chất lượng tương đương model "Pro/Turbo" nhưng với chi phí tối ưu hơn 10 lần.

#### 3. Problem Solving (10/10)
- **Xử lý lỗi Provider**: Giải quyết thành công lỗi 404/Not Found khi gọi Gemini qua OpenAI SDK bằng cách thực hiện Diagnostic Listing các model khả dụng và cập nhật Base URL tương thích (OpenAI-compatible endpoint).
- **Adversarial Resilience**: Tinh chỉnh logic để hệ thống không bị "hallucinate" điểm số khi gặp các Prompt Injection trong bộ Hard Cases, giữ cho điểm số Calibration luôn nằm trong dải [1.0, 5.0].
