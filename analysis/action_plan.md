# Lab14 - Báo cáo Việc Cần Làm & Kế Hoạch Thực Hiện

> Ghi chú: Khi `Get-Content` trong PowerShell, nội dung tiếng Việt/emoji có thể hiển thị lỗi (mojibake). File trong repo nên được lưu UTF-8 và xem trực tiếp trong editor/GitHub để kiểm tra.

## 1) Yêu cầu từ các file `.md` (tóm tắt theo deliverables)

Nguồn:
- `README.md`: chạy `python data/synthetic_gen.py` tạo `data/golden_set.jsonl`; chạy `python main.py` tạo `reports/summary.json` + `reports/benchmark_results.json`; hoàn thiện `analysis/failure_analysis.md`; thêm reflection cá nhân trong `analysis/reflections/`.
- `GRADING_RUBRIC.md`: bắt buộc có Retrieval Eval (Hit Rate + MRR), Multi-judge (>=2 model + agreement + xử lý xung đột), Regression gate V1 vs V2, async nhanh, báo cáo cost/token, failure analysis + 5 whys.
- `data/HARD_CASES_GUIDE.md`: cần hard cases (prompt injection, out-of-context, ambiguous, conflicting info, multi-turn, latency/cost stress).
- `analysis/failure_analysis.md`: hiện là template, cần điền số liệu thật + clustering + 5 whys + action plan.

## 2) Hiện trạng codebase (gap chính)

### Dataset/SDG
- `data/synthetic_gen.py` đang là placeholder: chỉ sinh 1 case mẫu, chưa 50+ cases, chưa hard cases, chưa có `expected_retrieval_ids` (ground-truth doc IDs).

### Retrieval evaluation
- `engine/retrieval_eval.py` có khung Hit Rate/MRR, nhưng:
  - Dataset hiện tại chưa có `expected_retrieval_ids`.
  - Agent chưa trả `retrieved_ids`.
  - Chưa được “đấu nối” vào pipeline tạo `reports/summary.json`.

### Judge/Evaluator
- `main.py` dùng `ExpertEvaluator`/`MultiModelJudge` giả lập điểm.
- `engine/llm_judge.py` giả lập 2 điểm số, chưa gọi model thật, chưa có conflict resolution, chưa có calibration/reliability ngoài agreement rate đơn giản.

### Regression gate & Reports
- `main.py` chạy V1/V2 nhưng thực tế đang dùng logic giả lập nên delta không có ý nghĩa.
- Report hiện ghi summary của V2; cần có so sánh V1 vs V2 theo nhiều metric và ngưỡng release/rollback.

### Submission checklist
- Thiếu `analysis/reflections/reflection_[Ten_SV].md` (README yêu cầu).

## 3) Kế hoạch từng bước (ưu tiên theo rubric/chấm điểm)

### Bước 0: Chốt schema & mục tiêu đo lường (bắt buộc)
- Chốt schema `data/golden_set.jsonl` tối thiểu:
  - `case_id`, `question`, `expected_answer`
  - `expected_retrieval_ids` (list doc/chunk ids)
  - `metadata`: `difficulty`, `type/tags` (hard-case tags)
  - (tuỳ chọn) `conversation` hoặc `turns` cho multi-turn
- Chốt output agent cần trả:
  - `answer`, `contexts` (list text), `retrieved_ids` (list ids), `metadata` (model/tokens/cost nếu có)

### Bước 1: Dựng corpus + doc IDs (để có ground truth retrieval)
- Tạo nguồn tài liệu có `doc_id` rõ ràng (VD: `data/docs.jsonl` hoặc thư mục PDF + index).
- Có bước ingestion/chunking + vector store (tối thiểu chạy local).

### Bước 2: SDG tạo 50+ cases + hard cases
- Nâng `data/synthetic_gen.py` để:
  - Sinh >= 50 cases.
  - Mỗi case gắn `expected_retrieval_ids`.
  - Bảo đảm có hard cases theo `data/HARD_CASES_GUIDE.md` (prompt injection, out-of-context, ambiguous, conflicting, multi-turn, latency/cost).

### Bước 3: Agent RAG thật (retrieval -> generation)
- Sửa `agent/main_agent.py` để:
  - Thực hiện retrieval từ vector store.
  - Trả về `retrieved_ids` và `contexts`.
  - Có cơ chế “không biết” khi out-of-context (giảm hallucination).

### Bước 4: Đấu nối Retrieval metrics (Hit Rate + MRR)
- Dùng `engine/retrieval_eval.py` tính per-case và average:
  - Hit Rate@k (k=3 hoặc 5, thống nhất).
  - MRR.
- Đưa kết quả vào `reports/summary.json` và (nếu cần) per-case vào `reports/benchmark_results.json`.

### Bước 5: Answer quality metrics (RAGAS) + latency/cost
- Tính RAGAS (faithfulness, relevancy) dựa trên `contexts` + `expected_answer`.
- Runner thu:
  - `latency` per-case, aggregate p50/p95.
  - `tokens_used`/`cost` (nếu LLM provider trả về; nếu không, ước lượng theo pricing + token usage).

### Bước 6: Multi-judge consensus (>=2 model)
- Implement thật trong `engine/llm_judge.py`:
  - Gọi ít nhất 2 judge models.
  - Tính `agreement_rate` và lưu `individual_scores`.
  - Xử lý xung đột khi lệch > 1 điểm:
    - Cách A: thêm tie-break judge thứ 3.
    - Cách B: rule-based (ưu tiên judge “stricter”) + ghi lý do.
  - (Nâng cao) check position bias: đảo A/B và so sánh.

### Bước 7: Regression gate (Release/Rollback)
- Chạy benchmark cho V1 và V2 là 2 cấu hình khác nhau (prompt/retriever/chunking):
  - So sánh: avg judge score, hit_rate, mrr, RAGAS, latency, cost.
  - Đặt ngưỡng rõ ràng (VD: avg_score không giảm quá X, hit_rate không giảm, cost không tăng quá Y%).
- Xuất report regression (có thể gộp vào `summary.json` hoặc file riêng).

### Bước 8: Failure analysis + reflections (file nộp)
- Điền `analysis/failure_analysis.md` bằng số liệu thật:
  - Pass/Fail, trung bình RAGAS, trung bình judge.
  - Failure clustering theo nhóm lỗi.
  - 3 case tệ nhất làm 5 Whys, chốt root cause.
  - Action plan cụ thể (chunking, rerank, prompt, ingestion, guardrails).
- Tạo `analysis/reflections/reflection_[Ten_SV].md` cho từng thành viên.

## 4) Checklist chạy cuối (trước khi nộp)
- `pip install -r requirements.txt`
- `python data/synthetic_gen.py` -> tạo `data/golden_set.jsonl` (không commit sẵn)
- `python main.py` -> tạo `reports/summary.json` + `reports/benchmark_results.json`
- `python check_lab.py` -> pass format + có cảnh báo/thiếu metric thì sửa ngay

