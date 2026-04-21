# Tài liệu triển khai Bước 1 và Bước 2

## Mục tiêu

Tài liệu này mô tả phần đã hoàn thành cho:

- **Bước 1:** Dựng corpus có `doc_id` / `chunk_id` rõ ràng để làm ground truth cho retrieval.
- **Bước 2:** Sinh golden dataset `50+` cases có `expected_retrieval_ids` và bao phủ hard cases.

Phạm vi tài liệu chỉ bao gồm phần đã triển khai, không bao gồm các bước RAG agent, retrieval metrics wiring, multi-judge hay regression gate.

---

## Các file đã thêm / cập nhật

### 1. `engine/corpus.py`

File này là lớp nền cho ingestion và corpus manifest.

Chức năng chính:

- Đọc toàn bộ tài liệu từ `data/docs/*.txt`.
- Chuẩn hóa metadata document:
  - `doc_id`
  - `title`
  - `source_path`
  - `department`
  - `effective_date`
  - `access_level`
- Tách tài liệu thành section dựa trên marker `=== ... ===`.
- Tạo chunk-level records với:
  - `chunk_id`
  - `doc_id`
  - `section_index`
  - `section_title`
  - `token_count`
  - `text`
- Sinh local vector store đơn giản bằng embedding deterministic dựa trên hashing token.
- Đồng bộ dữ liệu vào Chroma local collection `day14_docs`.

Artifact tạo ra:

- `data/docs.jsonl`
- `data/chunks.jsonl`
- `data/vector_store.json`
- `chroma_db/` (persistent Chroma store)

### 2. `index.py`

File này được chuyển thành entrypoint ingestion thực tế.

Khi chạy:

```bash
python index.py
```

script sẽ:

- build lại corpus
- sinh lại manifests
- sync lại Chroma collection local

### 3. `data/synthetic_gen.py`

File này được viết lại từ placeholder thành generator deterministic cho golden dataset.

Chức năng chính:

- Gọi `build_corpus(...)` trước khi sinh dataset để đảm bảo corpus và chunk ids luôn tồn tại.
- Tạo `68` test cases.
- Mỗi case đều có:
  - `case_id`
  - `question`
  - `expected_answer`
  - `expected_retrieval_ids`
  - `metadata`
- Một số case có thêm `conversation` để phục vụ multi-turn evaluation sau này.

Output:

- `data/golden_set.jsonl`

---

## Thiết kế corpus

## Nguồn tài liệu

Corpus hiện lấy từ 5 tài liệu text trong `data/docs/`:

- `access_control_sop.txt`
- `hr_leave_policy.txt`
- `it_helpdesk_faq.txt`
- `policy_refund_v4.txt`
- `sla_p1_2026.txt`

## Quy ước định danh

### Document ID

`doc_id` được lấy từ tên file, ví dụ:

- `access_control_sop`
- `hr_leave_policy`
- `it_helpdesk_faq`

### Chunk ID

`chunk_id` theo format:

```text
{doc_id}:section_{NN}
```

Ví dụ:

- `access_control_sop:section_02`
- `sla_p1_2026:section_03`

Quy ước này giúp:

- map retrieval result trực tiếp về ground truth
- tính Hit Rate / MRR dễ dàng ở bước sau
- trace failure theo section cụ thể thay vì theo document chung chung

## Chiến lược chunking

Hiện tại chunking theo **section-level**.

Lý do:

- tài liệu nguồn đã có cấu trúc section rõ ràng
- đủ nhỏ để truy vết retrieval
- chưa cần phức tạp hóa bằng sentence chunking hay sliding window ở bước đầu

Kết quả hiện tại:

- `5` documents
- `29` chunks

---

## Thiết kế dataset

## Schema của mỗi test case

Mỗi dòng trong `data/golden_set.jsonl` là một JSON object có schema:

```json
{
  "case_id": "access-01",
  "question": "Level 4 Admin Access cần những ai phê duyệt?",
  "expected_answer": "Level 4 Admin Access cần IT Manager và CISO phê duyệt...",
  "expected_retrieval_ids": ["access_control_sop:section_02"],
  "metadata": {
    "difficulty": "easy",
    "tags": ["factoid", "access-control"],
    "skip_retrieval_eval": false
  }
}
```

Một số case multi-turn có thêm:

```json
{
  "conversation": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "..."}
  ]
}
```

## Phân nhóm case

Dataset hiện chia theo domain:

- Access Control
- HR / Leave / Remote Work
- IT Helpdesk
- Refund Policy
- SLA / Incident Management
- Cross-document reasoning

## Hard cases đã bao phủ

Dataset đã có các nhóm hard cases theo `data/HARD_CASES_GUIDE.md`:

- `prompt-injection`
- `goal-hijacking`
- `out-of-context`
- `ambiguous`
- `conflicting-info`
- `multi-turn`
- `latency-stress`
- `cost-efficiency`
- `multi-doc`
- `reasoning`

## Thống kê hiện tại

Sau khi chạy generator:

- Tổng số case: `68`
- Difficulty mix:
  - `easy`: `37`
  - `medium`: `17`
  - `hard`: `14`

Điểm cần lưu ý:

- Bộ dữ liệu hiện là **deterministic**, không phụ thuộc API bên ngoài.
- Điều này giúp benchmark lặp lại ổn định trong lab.

---

## Cách chạy lại

### Build corpus + dataset

```bash
python data/synthetic_gen.py
```

Lệnh này sẽ:

1. build lại corpus
2. sinh lại manifests / vector store
3. tạo `data/golden_set.jsonl`

### Chỉ build lại index / corpus

```bash
python index.py
```

Lệnh này hữu ích khi:

- thay đổi tài liệu trong `data/docs/`
- muốn rebuild chunk manifests
- muốn resync Chroma local

---

## Artifact đầu ra

Sau Bước 1 và Bước 2, repo có các artifact sau:

- `data/docs.jsonl`: manifest document-level
- `data/chunks.jsonl`: manifest chunk-level
- `data/vector_store.json`: vector store local dạng JSON
- `data/golden_set.jsonl`: benchmark dataset có ground truth retrieval ids
- `chroma_db/`: persistent local vector DB

---

## Quyết định kỹ thuật

### 1. Không dùng embedding model ngoài

Embedding hiện tại là deterministic hashing-based embedding.

Lý do:

- chạy local, không cần network
- không phụ thuộc model download
- đủ để thiết lập pipeline ingestion / retrieval ground truth

Tradeoff:

- chất lượng semantic retrieval không cao bằng embedding model thật
- phù hợp cho Bước 1–2, chưa phải retrieval production-grade

### 2. Không dùng SDG bằng LLM

Dataset hiện được viết theo rule-based curated cases thay vì gọi LLM để SDG.

Lý do:

- reproducible
- nhanh
- tránh phụ thuộc API key
- kiểm soát được hard-case coverage

Tradeoff:

- độ đa dạng ngôn ngữ còn giới hạn
- chưa có paraphrase phong phú như LLM-generated dataset

### 3. Chunk ở mức section

Section-level chunking đơn giản hơn sentence-level.

Lý do:

- ground truth retrieval dễ gán
- phù hợp với cấu trúc tài liệu chính sách / SOP

Tradeoff:

- một số section còn khá dài
- sau này có thể cần chia nhỏ thêm để tăng precision retrieval

---

## Giới hạn hiện tại

Bước 1–2 mới chuẩn bị dữ liệu. Các phần sau **chưa được nối hoàn chỉnh**:

- `agent/main_agent.py` chưa retrieval thật từ corpus mới
- `engine/retrieval_eval.py` chưa được đấu nối end-to-end vào pipeline benchmark
- `main.py` vẫn đang dùng evaluator / judge placeholder

Nói ngắn gọn: dữ liệu nền cho retrieval evaluation đã sẵn sàng, nhưng benchmark pipeline tổng thể vẫn cần triển khai tiếp ở các bước sau.

---

## Bước tiếp theo đề xuất

Ưu tiên tiếp theo:

1. cập nhật `agent/main_agent.py` để trả về `retrieved_ids` và `contexts`
2. dùng `engine/retrieval_eval.py` để tính Hit Rate / MRR trên `expected_retrieval_ids`
3. ghi retrieval metrics vào `reports/summary.json` và `reports/benchmark_results.json`

