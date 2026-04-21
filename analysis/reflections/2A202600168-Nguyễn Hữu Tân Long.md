# Individual Reflection — Tan Long

## 1. Đóng góp cá nhân

### Retrieval Evaluation & Metrics Integration
Tôi phụ trách tích hợp **Hit Rate** và **MRR** vào pipeline đánh giá — phần quan trọng nhất để chứng minh chất lượng Retrieval stage trước khi đánh giá Generation.

**Thay đổi kỹ thuật thực hiện:**
- `agent/main_agent.py`: Bổ sung `retrieved_ids` vào response của `query()`, cho phép tracking chính xác những chunk nào được lấy về.
- `engine/runner.py`: Tích hợp `RetrievalEvaluator` vào benchmark pipeline — tự động tính Hit Rate @3 và MRR @3 cho từng test case và aggregate vào `summary.json`.
- `reports/summary.json`: Bổ sung hai chỉ số `hit_rate: 0.8378` và `mrr: 0.7477` vào phần metrics.

**Kết quả đạt được:**
- Hit Rate @3: **83.78%** (62/74 cases tìm được đúng tài liệu)
- MRR @3: **0.7477** (trung bình rank của tài liệu đúng là ~1.3)
- `check_lab.py` không còn warning về thiếu retrieval metrics.

### Failure Analysis & Root Cause Investigation
Phân tích toàn bộ **13 failure cases** từ `benchmark_results.json`, phân nhóm theo loại lỗi, và thực hiện 5 Whys cho 3 case tệ nhất. Kết quả ghi trong `analysis/failure_analysis.md`.

---

## 2. Giải thích kỹ thuật chuyên sâu

### MRR (Mean Reciprocal Rank) là gì và tại sao quan trọng hơn Hit Rate?

Hit Rate chỉ cho biết "có tìm thấy không" (binary), còn MRR đo **vị trí** của tài liệu đúng trong kết quả:

```
MRR = (1/N) * Σ (1 / rank_i)
```

Ví dụ: Nếu tài liệu đúng luôn ở vị trí 1 → MRR = 1.0. Nếu luôn ở vị trí 3 → MRR = 0.33.

Với hệ thống RAG, MRR cao hơn Hit Rate là tốt — có nghĩa là khi tìm được, tài liệu đúng thường ở **top đầu**, được đưa vào context trước. Trong kết quả của chúng tôi: Hit Rate = 0.84, MRR = 0.75 — khoảng cách này cho thấy ~9% cases tìm được tài liệu đúng nhưng ở **rank 2 hoặc 3**, không phải rank 1.

### Cohen's Kappa vs Agreement Rate

Hệ thống dùng Agreement Rate tự tính (70% pairwise + 30% variance smoothness). Đây là metric **không calibrated**. Cohen's Kappa chuẩn hơn vì loại trừ yếu tố agreement ngẫu nhiên:

```
κ = (P_observed - P_chance) / (1 - P_chance)
```

Agreement Rate 93% của chúng tôi không tương đương κ = 0.93. Với scale 1-5, P_chance ≈ 0.2, nên κ thực tế có thể ở khoảng 0.91. Vẫn là "Almost Perfect Agreement" theo thang Landis & Koch, nhưng không nên báo cáo nhầm.

### Position Bias trong LLM Judge

GPT-4o-mini và các LLM judge có xu hướng **ưa vị trí đầu** (primacy bias) — câu trả lời được trình bày trước thường được đánh giá cao hơn. Trong `engine/llm_judge.py` đã có code phát hiện position bias, nhưng chưa được kích hoạt trong pipeline chính. Đây là rủi ro tiềm ẩn khi so sánh hai agent version.

### Trade-off Chi phí vs Chất lượng

| Strategy | Chi phí/eval | Độ chính xác | Ghi chú |
|----------|-------------|-------------|---------|
| 1 Judge (GPT-4o-mini) | ~$0.0003 | Baseline | Rủi ro position bias |
| 2 Judges + Arbitrator | ~$0.0009 | +8-12% | Chiến lược hiện tại |
| 3 Judges đầy đủ | ~$0.0012 | +15% | Overkill cho most cases |
| Mock Judge | $0 | 0% | Chỉ dùng để dev/test |

Để giảm 30% chi phí mà không giảm chất lượng: chỉ gọi Arbitrator khi score diff > 1.5 (thay vì > 1.0), ước tính tiết kiệm ~60% số lần gọi arbitrator với conflict rate hiện tại là 4%.

---

## 3. Vấn đề gặp phải và cách giải quyết

**Vấn đề 1: Hash-based embedding không capture ngữ nghĩa**  
Khi debug các Retrieval Miss cases (SLA P1/P2, version changelog), tôi nhận ra vector search với SHA-256 hash embedding chỉ match exact-token chứ không match theo nghĩa. Câu hỏi "P1 SLA" không match chunk "Priority 1 — 15 phút" vì "P1" ≠ "Priority 1" trong không gian vector. Giải pháp ngắn hạn là tăng top_k; giải pháp dài hạn là migrate sang `sentence-transformers`.

**Vấn đề 2: Failure cases Prompt Injection có điểm thấp dù agent "đúng"**  
Agent từ chối yêu cầu malicious là **đúng về mặt security**, nhưng Judge chấm điểm thấp vì câu trả lời không helpful. Phân tích 5 Whys cho thấy đây là vấn đề **evaluation criteria** chứ không phải lỗi agent — cần thêm rubric riêng cho security cases trong judge prompt.

---

## 4. Kết luận

Lab 14 cho tôi thấy rằng đánh giá AI không chỉ là "chạy một LLM và cho điểm". Retrieval quality ảnh hưởng trực tiếp đến generation quality — 6/13 failures xuất phát từ retrieval miss, không phải LLM kém. Multi-judge consensus với 93% agreement rate chứng minh hệ thống đáng tin cậy, nhưng vẫn cần calibration (Cohen's Kappa) để đảm bảo tính khách quan trong môi trường production.
