# Báo cáo cá nhân — Lab 7: Embedding & Vector Store

**Sinh viên:** Đinh Hoàng Đức — 2A202602795
**Ngày chạy benchmark:** 2026-09-20

## 1. Phạm vi dữ liệu

Benchmark cá nhân dùng corpus `data/shopee-buyer-policy/` gồm 5 bài viết công khai từ Shopee Trung tâm trợ giúp, phục vụ người mua (`audience: buyer`). Danh sách URL, ngày thu thập và phiên bản nằm tại `data/urls.csv` và `data/shopee-buyer-policy/sources.csv`.

| `doc_id` | Nội dung chính | `category` | `document_version` |
|---|---|---|---|
| `shopee-buyer-return-refund-request` | Gửi yêu cầu Trả hàng/Hoàn tiền | `return-refund` | `not-stated` |
| `shopee-buyer-dispute-process` | Giải quyết tranh chấp và khiếu nại | `dispute` | `2024-03-15` |
| `shopee-buyer-order-cancellation` | Hủy đơn hàng của người mua | `order-cancellation` | `not-stated` |
| `shopee-buyer-cancelled-order-rules` | Quy định đơn hàng đã hủy | `order-cancellation` | `not-stated` |
| `shopee-buyer-delivery-status-issue` | Trạng thái giao hàng cập nhật sai | `delivery-issue` | `not-stated` |

Không có dữ liệu cá nhân, thông tin đăng nhập hoặc nguồn sau đăng nhập trong corpus. Với bài tranh chấp, ngày `2024-03-15` được nêu trong chính nội dung nguồn; các bài còn lại không công bố phiên bản nên ghi `not-stated`.

## 2. Hoàn thiện mã nguồn

- `SentenceChunker` gom tối đa số câu đã cấu hình.
- `RecursiveChunker` ưu tiên tách theo đoạn, xuống dòng, câu, khoảng trắng rồi ký tự.
- `compute_similarity` tính cosine similarity và trả `0.0` khi một vector có độ lớn bằng 0.
- `EmbeddingStore` hỗ trợ thêm, tìm kiếm, lọc metadata và xóa theo `doc_id`.
- `KnowledgeBaseAgent` ghép top-k context và yêu cầu câu trả lời chỉ dựa trên context.

Đã chạy trong WSL với Python 3.12.3:

```text
44 passed in 0.47s
```

Trong đó có một kiểm thử hồi quy cho `bench.py`: benchmark phải nhận diện Shopee buyer-policy corpus và dùng `metadata_filter={'audience': 'buyer'}`.

## 3. Kiểm tra cosine với MockEmbedder

Bảng này được chạy bằng `MockEmbedder` và `compute_similarity` trên 2026-09-20. MockEmbedder sinh vector xác định từ MD5, do đó kết quả chỉ kiểm tra phép tính cosine; không được dùng làm bằng chứng về độ tương đồng ngữ nghĩa.

| # | Cặp câu | Kỳ vọng ngữ nghĩa | Cosine thực tế |
|---:|---|---|---:|
| 1 | Đơn đã hủy không thể khôi phục / Đơn `Đã hủy` không được giao lại | gần nghĩa | -0.0416 |
| 2 | Xử lý yêu cầu 3–5 ngày / Hoàn tiền 1–14 ngày | cùng chủ đề, khác mốc thời gian | -0.2707 |
| 3 | Shipper liên hệ 3 lần / Chờ phản hồi Người bán khi `Chờ lấy hàng` | khác quy trình | 0.1274 |
| 4 | Chọn lý do `Chưa nhận được hàng` / Không cần bằng chứng cho lý do này | gần nghĩa | -0.0399 |
| 5 | `Chờ xác nhận` hủy ngay / Đơn chuyển hoàn không thể giao lại | khác trạng thái | -0.0951 |

Điểm cao nhất lại thuộc cặp khác quy trình (cặp 3), còn các cặp gần nghĩa có điểm âm. Vì vậy benchmark retrieval bên dưới dùng Gemini embedding thay vì MockEmbedder.

## 4. Benchmark retrieval trên buyer corpus

Lệnh chạy tạo ba artifact là:

```bash
python bench.py --embedding-provider gemini --chunker recursive --output ket_qua_benchmark.txt
python bench.py --embedding-provider gemini --chunker fixed --output ket_qua_benchmark_fixed.txt
python bench.py --embedding-provider gemini --chunker sentence --output ket_qua_benchmark_sentence.txt
```

Backend là `gemini-embedding-001`, `top_k=3`; phần trả lời dùng hàm extractive cục bộ của `bench.py`. Mỗi câu được chấm thủ công 0–2: 1 điểm khi evidence chứa gold answer có mặt trong top-3 và thêm 1 điểm khi câu trả lời extractive nêu đủ thông tin gold.

| # | Câu hỏi rút gọn | Nguồn gold | Recursive | Fixed | Sentence |
|---:|---|---|---:|---:|---:|
| 1 | Gửi Trả hàng/Hoàn tiền tại trang đơn | `return-refund-request` | 1 | 1 | 2 |
| 2 | Thời gian xử lý và hoàn tiền | `return-refund-request` | 1 | 1 | 1 |
| 3 | Trạng thái có thể yêu cầu hủy | `order-cancellation` | 1 | 1 | 2 |
| 4 | Shipper không liên hệ nhưng báo giao thất bại | `delivery-status-issue` | 2 | 2 | 1 |
| 5 | Quá 24 giờ báo đã giao nhưng chưa nhận hàng | `delivery-status-issue` | 2 | 1 | 1 |
| **Tổng câu trả lời /10** |  |  | **7** | **6** | **7** |

Cả ba chiến lược đều có evidence cho 5/5 gold answer trong top-3. Điểm không tối đa là do agent extractive thường lấy các câu đầu của chunk: Recursive và Fixed ở câu 1 chỉ trả phần giới thiệu, còn Sentence ở câu 4 và 5 chỉ lấy heading. Các chi tiết này có thể kiểm tra trực tiếp trong ba file `ket_qua_benchmark*.txt`.

| Chiến lược | Cấu hình | Số chunks | Điểm top-1 theo Q1→Q5 |
|---|---|---:|---|
| Recursive | `chunk_size=700` | 27 | 0.8221, 0.8010, 0.8339, 0.8283, 0.7851 |
| Fixed | `chunk_size=700`, `overlap=70` | 25 | 0.8175, 0.7920, 0.8357, 0.8320, 0.7751 |
| Sentence | tối đa 3 câu/chunk | 34 | 0.8200, 0.8338, 0.8467, 0.8216, 0.7832 |

## 5. Metadata filter và giới hạn

Ở câu 5, `search(...)` và `search_with_filter(..., {'audience': 'buyer'})` trả cùng top-3 trong cả ba lượt chạy. Đây là kết quả đúng với corpus hiện tại vì cả 5/5 tài liệu đều có `audience: buyer`; filter không loại được tài liệu nào nên không chứng minh được cải thiện precision.

Không suy ra từ thí nghiệm này rằng metadata filter làm retrieval tốt hơn. Muốn đo tác động thực tế cần bổ sung tài liệu có audience khác và một query mà filter loại được kết quả sai.

## 6. Kết luận cá nhân

Recursive và Sentence cùng đạt 7/10 cho câu trả lời extractive trên bộ 5 query hiện tại; Fixed đạt 6/10. Không có cơ sở để khẳng định một chiến lược thắng tuyệt đối: Sentence trả đúng đầy đủ Q1/Q3, còn Recursive trả đúng đầy đủ Q4/Q5. Kết quả, số chunk, score và các failure case trong báo cáo này đều lấy từ lần chạy lưu trong repository.
