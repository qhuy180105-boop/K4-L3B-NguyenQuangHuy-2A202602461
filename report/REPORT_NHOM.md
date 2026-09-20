# Báo cáo nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** T153
**Thành viên đã có thông tin trong repository:** Đinh Hoàng Đức — 2A202602795
**Ngày chạy benchmark:** 2026-09-20

> Repository không có họ tên/mã sinh viên của các thành viên còn lại. Báo cáo không tự điền thông tin này; nhóm cần bổ sung nếu có trước khi nộp.

## 1. Dữ liệu được chọn

Nhóm dùng 5 tài liệu công khai trên Shopee Trung tâm trợ giúp về quy trình dành cho người mua: gửi Trả hàng/Hoàn tiền, tranh chấp/khiếu nại, hủy đơn, đơn đã hủy và trạng thái giao hàng cập nhật sai. Corpus nằm tại `data/shopee-buyer-policy/`; URL gốc và provenance một-một được lưu trong `data/shopee-buyer-policy/sources.csv`.

| `doc_id` | Chủ đề | `audience` | Ngày lấy | Phiên bản |
|---|---|---|---|---|
| `shopee-buyer-return-refund-request` | Gửi yêu cầu Trả hàng/Hoàn tiền | `buyer` | 2026-09-20 | `not-stated` |
| `shopee-buyer-dispute-process` | Tranh chấp và khiếu nại | `buyer` | 2026-09-20 | `2024-03-15` |
| `shopee-buyer-order-cancellation` | Hủy đơn của người mua | `buyer` | 2026-09-20 | `not-stated` |
| `shopee-buyer-cancelled-order-rules` | Quy định đơn đã hủy | `buyer` | 2026-09-20 | `not-stated` |
| `shopee-buyer-delivery-status-issue` | Trạng thái giao hàng cập nhật sai | `buyer` | 2026-09-20 | `not-stated` |

Metadata dùng để truy vết gồm `doc_id`, `title`, `source_url`, `retrieved_at`, `document_version`, `audience`, `department`, `category` và `language`. Giá trị `language` đã chuẩn hóa là `vi`; bài tranh chấp là bài duy nhất trong corpus nêu ngày phiên bản 15-03-2024.

## 2. Thiết kế benchmark

Ba chiến lược chạy trên cùng corpus, cùng 5 query, `top_k=3` và Gemini `gemini-embedding-001`:

| Chiến lược | Cấu hình | Artifact |
|---|---|---|
| Recursive | `RecursiveChunker(chunk_size=700)` | `ket_qua_benchmark.txt` |
| Fixed | `FixedSizeChunker(chunk_size=700, overlap=70)` | `ket_qua_benchmark_fixed.txt` |
| Sentence | `SentenceChunker(max_sentences_per_chunk=3)` | `ket_qua_benchmark_sentence.txt` |

| # | Query | Gold answer rút gọn | Evidence nguồn |
|---:|---|---|---|
| 1 | Gửi yêu cầu Trả hàng/Hoàn tiền tại trang đơn như thế nào? | `Tôi` > `Chờ giao hàng/Đã giao` > chọn đơn > `Trả hàng/Hoàn tiền` | `return-refund-request` |
| 2 | Xử lý yêu cầu và hoàn tiền mất bao lâu? | 3–5 ngày làm việc; 1–14 ngày làm việc tùy phương thức | `return-refund-request` |
| 3 | Có thể yêu cầu hủy đơn ở trạng thái nào? | `Chờ xác nhận` hủy ngay; `Chờ lấy hàng` chờ phản hồi Người bán; trạng thái khác không thể yêu cầu | `order-cancellation` |
| 4 | Shipper không liên hệ nhưng báo giao thất bại thì làm gì? | Chờ cuộc gọi tiếp theo; Shipper có 3 lần liên hệ | `delivery-status-issue` |
| 5 | Quá 24 giờ báo đã giao nhưng chưa nhận hàng thì làm gì? | Chọn `Chưa nhận được hàng`; không cần bằng chứng | `delivery-status-issue` |

## 3. Kết quả benchmark thực tế

Kết quả dưới đây lấy trực tiếp từ ba artifact benchmark. `Gold evidence trong top-3` nghĩa là top-3 có chunk chứa thông tin để trả lời gold; `điểm câu trả lời` được chấm thủ công 0–2/câu (evidence 1 điểm, agent extractive nêu đủ gold 1 điểm).

| Chiến lược | Chunks | Gold evidence trong top-3 | Điểm câu trả lời /10 | Nhận xét có căn cứ |
|---|---:|---:|---:|---|
| Recursive 700 | 27 | 5 / 5 | 7 | Q4/Q5 đủ thông tin; Q1/Q3 chỉ trả phần mở đầu chunk, Q2 thiếu mốc xử lý 3–5 ngày. |
| Fixed 700, overlap 70 | 25 | 5 / 5 | 6 | Q4 đủ thông tin; Q1/Q3/Q5 chỉ lấy heading hoặc mở đầu, Q2 thiếu mốc xử lý 3–5 ngày. |
| Sentence, 3 câu | 34 | 5 / 5 | 7 | Q1/Q3 đủ thông tin; Q2 thiếu mốc xử lý 3–5 ngày, Q4/Q5 chỉ lấy heading. |

| # | Recursive top-1 / score | Fixed top-1 / score | Sentence top-1 / score |
|---:|---|---|---|
| 1 | `return-refund-request` / 0.8221 | `return-refund-request` / 0.8175 | `return-refund-request` / 0.8200 |
| 2 | `return-refund-request` / 0.8010 | `return-refund-request` / 0.7920 | `return-refund-request` / 0.8338 |
| 3 | `order-cancellation` / 0.8339 | `order-cancellation` / 0.8357 | `order-cancellation` / 0.8467 |
| 4 | `delivery-status-issue` / 0.8283 | `delivery-status-issue` / 0.8320 | `delivery-status-issue` / 0.8216 |
| 5 | `delivery-status-issue` / 0.7851 | `delivery-status-issue` / 0.7751 | `delivery-status-issue` / 0.7832 |

## 4. Metadata filter: kết quả và giới hạn

Query 5 chạy cả baseline và `search_with_filter(..., metadata_filter={'audience': 'buyer'})`. Cả hai cho đúng cùng top-3 và score trong cả ba chiến lược. Lý do là 5/5 tài liệu đều mang `audience: buyer`, nên bộ lọc không giảm không gian tìm kiếm.

Do đó, nhóm chỉ kết luận filter hoạt động tương thích với metadata hiện có; không có bằng chứng từ corpus này để nói filter tăng precision. Để đánh giá trade-off precision/recall, cần bổ sung ít nhất một nhóm tài liệu audience khác hoặc một trường metadata phân biệt hơn.

## 5. Bài học từ kết quả

- Gemini embedding đưa đúng nguồn chứa gold evidence vào top-3 cho cả 5 query ở cả ba chiến lược.
- Chất lượng retrieval chưa đồng nghĩa câu trả lời cuối cùng đầy đủ: hàm extractive hiện lấy các câu đầu context nên có thể bỏ mốc thời gian hoặc hướng dẫn nằm sau trong chunk.
- Fixed tạo ít chunks nhất (25), Sentence nhiều nhất (34); với bộ query này, Recursive và Sentence cùng đạt 7/10 cho phần trả lời extractive. Không đủ bằng chứng để chọn một chiến lược tốt nhất tuyệt đối.
- `doc_id` chỉ định nguồn chưa đủ để đánh giá; cần kiểm tra chunk cụ thể có gold answer và output agent có nêu đúng đầy đủ thông tin hay không.

## 6. Kiểm chứng mã nguồn

Toàn bộ test của repository được chạy bằng Python 3.12.3 trong WSL:

```text
44 passed in 0.47s
```

Kết quả này gồm kiểm thử hồi quy để ngăn `bench.py` quay lại corpus cũ hoặc dùng sai filter `audience`.

## 7. Nội dung cần bổ sung trước khi nộp

- Họ tên và mã sinh viên của thành viên nhóm chưa có trong repository.
- Phần tự đánh giá/điểm nhóm chỉ nên điền khi giảng viên hoặc nhóm có quy tắc chấm và bằng chứng tương ứng; báo cáo không tự gán điểm.
