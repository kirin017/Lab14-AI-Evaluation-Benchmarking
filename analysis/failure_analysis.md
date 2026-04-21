# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tổng số cases:** 74
- **Tỉ lệ Pass/Fail:** 63/11 (Pass threshold: 3.0)
- **Hệ số đồng thuận (Agreement Rate):** 0.93 (Very High)
- **Điểm LLM-Judge trung bình:** 4.18 / 5.0

## 2. Phân nhóm lỗi (Failure Clustering)
| Nhóm lỗi | Số lượng | Nguyên nhân dự kiến |
|----------|----------|---------------------|
| Reasoning | 5 | Agent không kết hợp được thông tin từ nhiều chunk (Multi-doc) |
| Hallucination | 3 | Agent trả lời sai quy định khi bị "tấn công" bằng Prompt Injection |
| Incomplete | 3 | Retrieval lấy thiếu context quan trọng (ví dụ: ngày onsite phụ) |

## 3. Phân tích 5 Whys (Chọn 3 case tệ nhất)

### Case #1: [Mô tả ngắn]
1. **Symptom:** Agent trả lời sai về...
2. **Why 1:** LLM không thấy thông tin trong context.
3. **Why 2:** Vector DB không tìm thấy tài liệu liên quan nhất.
4. **Why 3:** Chunking size quá lớn làm loãng thông tin quan trọng.
5. **Why 4:** ...
6. **Root Cause:** Chiến lược Chunking không phù hợp với dữ liệu bảng biểu.

## 4. Kế hoạch cải tiến (Action Plan)
- [ ] Thay đổi Chunking strategy từ Fixed-size sang Semantic Chunking.
- [ ] Cập nhật System Prompt để nhấn mạnh vào việc "Chỉ trả lời dựa trên context".
- [ ] Thêm bước Reranking vào Pipeline.
