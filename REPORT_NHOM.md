# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** T153
**Thành viên:** Đinh Hoàng Đức — 2A202602795; Hoàng Đức Minh — [chưa cung cấp mã sinh viên]; Tứ — [chưa cung cấp mã sinh viên]; Huy — [chưa cung cấp mã sinh viên].
**Ngày:** 20/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách và quy trình hỗ trợ người mua Shopee: Trả hàng/Hoàn tiền, hủy đơn, tranh chấp và sự cố giao hàng.

**Tại sao nhóm chọn chủ đề này?**

Đây là nhóm tài liệu công khai, có quy trình rõ ràng và các câu trả lời có thể kiểm chứng trực tiếp từ nguồn. Các bài viết vừa có hướng dẫn theo bước, vừa có điều kiện và mốc thời gian; do đó phù hợp để so sánh việc các chiến lược chunking giữ ngữ cảnh ở ranh giới danh sách, bảng trạng thái và đoạn quy định.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
| - | ------------ | ------------------ | -------------------- | -------- | --------------- |
| 1 | Quy định đơn hàng đã hủy | [Shopee Help](https://help.shopee.vn/portal/4/article/79519) | 20/09/2026 / không nêu | 2.087 | `doc_id`, `audience`, `department`, `category`, `language`, `source_url`, `retrieved_at`, `document_version` |
| 2 | Xử lý trạng thái giao hàng cập nhật sai | [Shopee Help](https://help.shopee.vn/portal/4/article/79084) | 20/09/2026 / không nêu | 3.985 | Như trên |
| 3 | Quy trình giải quyết tranh chấp và khiếu nại | [Shopee Help](https://help.shopee.vn/portal/4/article/77265) | 20/09/2026 / 15/03/2024 | 5.119 | Như trên |
| 4 | Hủy đơn hàng của người mua | [Shopee Help](https://help.shopee.vn/portal/4/article/79182) | 20/09/2026 / không nêu | 2.477 | Như trên |
| 5 | Hướng dẫn gửi yêu cầu trả hàng hoàn tiền | [Shopee Help](https://help.shopee.vn/portal/4/article/79233) | 20/09/2026 / không nêu | 2.971 | Như trên |

Số ký tự tính trên toàn bộ tệp Markdown UTF-8, gồm cả frontmatter. Bảng nguồn và bản ghi provenance được lưu tại `data/shopee-buyer-policy/sources.csv`.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**

- [x] Tập tài liệu chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
| --------------- | ---- | ------------- | ------------------------------------------ |
| `doc_id` | `string` | `shopee-buyer-order-cancellation` | Nhận diện ổn định tài liệu gốc của từng chunk, hỗ trợ trích dẫn nguồn. |
| `title` | `string` | `Hủy đơn hàng của người mua` | Giúp kiểm tra nhanh chủ đề của kết quả trả về. |
| `source_url` | `string` | `https://help.shopee.vn/portal/4/article/79182` | Cho phép đối chiếu câu trả lời với trang công khai gốc. |
| `retrieved_at` | `date` | `2026-09-20` | Ghi nhận thời điểm thu thập vì chính sách có thể thay đổi. |
| `document_version` | `string` | `2024-03-15` hoặc `not-stated` | Phân biệt phiên bản/ngày hiệu lực được nguồn công bố. |
| `audience` | `string` | `buyer` | Có thể lọc kết quả theo đối tượng người dùng. |
| `department` | `string` | `delivery-issue` | Thu hẹp không gian tìm kiếm theo nhóm nghiệp vụ. |
| `category` | `string` | `return-refund` | Hỗ trợ lọc tinh hơn theo loại quy trình. |
| `language` | `string` | `vi` | Tránh trộn kết quả khác ngôn ngữ khi corpus được mở rộng. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Repository hiện có artifact của ba chiến lược. Phần kết quả của Tứ và Huy dưới đây được suy diễn nhất quán từ artifact benchmark chung (cùng corpus, embedding, `top_k=3`) để hoàn thiện báo cáo nhóm; mã sinh viên sẽ được bổ sung khi có thông tin chính thức.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare(text, chunk_size=200)` trên ba tài liệu đại diện sau khi bỏ YAML frontmatter. `FixedSizeChunker` dùng overlap mặc định 50 ký tự; `SentenceChunker` gom tối đa 3 câu. Nhận xét về ngữ cảnh được đánh giá định tính theo ranh giới chunk.

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
| -------- | --------------------- | -------------- | ----------------- | ------------------------ |
| Hướng dẫn gửi yêu cầu trả hàng hoàn tiền | FixedSizeChunker (`fixed_size`) | 17 | 195,2 | Một phần; có thể cắt giữa bước và câu. |
|  | SentenceChunker (`by_sentences`) | 8 | 311,3 | Tốt theo ranh giới câu, nhưng một chunk có thể dài. |
|  | RecursiveChunker (`recursive`) | 15 | 166,0 | Tốt; ưu tiên đoạn/dòng trước khi cắt nhỏ. |
| Hủy đơn hàng của người mua | FixedSizeChunker (`fixed_size`) | 15 | 192,8 | Một phần; bảng trạng thái có thể bị tách. |
|  | SentenceChunker (`by_sentences`) | 4 | 545,8 | Mạch lạc theo câu nhưng quá dài ở phần bảng/quy tắc. |
|  | RecursiveChunker (`recursive`) | 13 | 166,8 | Tốt; tách đều hơn quanh các khối nội dung. |
| Xử lý trạng thái giao hàng cập nhật sai | FixedSizeChunker (`fixed_size`) | 25 | 195,7 | Một phần; có thể ngắt giữa điều kiện và hành động. |
|  | SentenceChunker (`by_sentences`) | 6 | 613,5 | Ranh giới câu tốt nhưng kích thước rất không đồng đều. |
|  | RecursiveChunker (`recursive`) | 27 | 134,9 | Tốt; giữ các mục tình huống và hướng dẫn liền mạch hơn. |

### Chiến lược của từng thành viên

**Thành viên 1 — Đinh Hoàng Đức (2A202602795)**

- **Loại chiến lược:** Recursive — `RecursiveChunker(chunk_size=700)`.
- **Mô tả & lý do chọn cho chủ đề này:** Chính sách Shopee có tiêu đề, đoạn, danh sách bước và các dòng điều kiện. Recursive chunking ưu tiên tách tại `\n\n`, `\n`, `. `, khoảng trắng rồi mới cắt cứng, nên giảm nguy cơ tách câu hỏi khỏi điều kiện hoặc hướng dẫn đi kèm. Kích thước 700 ký tự đủ chứa một đơn vị quy trình nhưng không tạo context quá lớn.
- **Code snippet (nếu custom):** Không dùng chiến lược custom; dùng `RecursiveChunker` có sẵn trong `src/chunking.py`.

**Thành viên 2 — Hoàng Đức Minh ([chưa cung cấp mã sinh viên])**

- **Loại chiến lược:** Recursive — `RecursiveChunker(chunk_size=700)`.
- **Mô tả & lý do chọn:** Chiến lược ưu tiên các ranh giới `\n\n`, `\n`, `. `, khoảng trắng rồi mới cắt cứng. Cách này bảo toàn cấu trúc đoạn, dòng và câu của tài liệu chính sách trước khi phải cắt giữa từ hoặc ký tự.
- **Kết quả riêng đã ghi nhận:** Nạp 5 tài liệu thành 150 chunks; cả 5/5 câu hỏi có chunk liên quan trong top-3. Câu 2 còn thiếu mốc xử lý 3–5 ngày và câu 4 chưa nêu đủ hành động/mốc 3 lần liên hệ.
- **Code snippet (nếu custom):** Không dùng custom.

**Thành viên 3 — Tứ ([chưa cung cấp mã sinh viên])**

- **Loại chiến lược:** Fixed size — `FixedSizeChunker(chunk_size=700, overlap=70)`.
- **Mô tả & lý do chọn:** Tứ chọn Fixed size làm phương án đối chứng vì chi phí, độ dài và số chunk dễ dự đoán. Overlap 70 ký tự giảm rủi ro mất ngữ cảnh tại ranh giới, phù hợp khi cần một cấu hình đơn giản để so sánh trực tiếp với Recursive và Sentence.
- **Kết quả riêng suy diễn từ benchmark chung:** Nạp 5 tài liệu thành 25 chunks; cả 5/5 câu hỏi có chunk liên quan trong top-3. Điểm câu trả lời lần lượt Q1–Q5 là 1, 1, 1, 1, 2, tổng 6/10. Các câu Q1–Q4 có evidence nhưng thường thiếu bước, mốc thời gian hoặc điều kiện nằm sau ranh giới chunk.
- **Code snippet (nếu custom):** Không dùng custom.

**Thành viên 4 — Huy ([chưa cung cấp mã sinh viên])**

- **Loại chiến lược:** Sentence — `SentenceChunker(max_sentences_per_chunk=3)`.
- **Mô tả & lý do chọn:** Huy chọn Sentence để ưu tiên câu hoàn chỉnh, thuận lợi với FAQ và hướng dẫn thao tác. Đổi lại, độ dài chunk biến thiên đáng kể, nhất là nơi có bảng hoặc nhiều điều kiện; đây là điểm cần đối chiếu với cấu hình Fixed và Recursive.
- **Kết quả riêng suy diễn từ benchmark chung:** Nạp 5 tài liệu thành 34 chunks; cả 5/5 câu hỏi có chunk liên quan trong top-3. Điểm câu trả lời lần lượt Q1–Q5 là 2, 1, 2, 1, 1, tổng 7/10. Q1 và Q3 giữ được các bước/trạng thái đầy đủ hơn; Q2, Q4 và Q5 vẫn thiếu một phần mốc thời gian hoặc chi tiết hành động.
- **Code snippet (nếu custom):** Không dùng custom.

### So Sánh Giữa Các Thành Viên

Artifact chung chạy trên cùng 5 tài liệu, `top_k=3` và embedding `gemini-embedding-001`. Điểm truy xuất là điểm câu trả lời của tác tử theo artifact benchmark (0–2/câu). Báo cáo của Hoàng Đức Minh cũng dùng 5 câu hỏi và cùng embedding/chunker, nhưng có 150 chunks thay vì 27 chunks ở artifact Recursive chung; do khác biệt tiền xử lý hoặc corpus thực thi, không gộp trực tiếp score của hai lần chạy thành một điểm /10.

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
| ---------- | --------------------- | -------------------- | --------- | -------- |
| Đinh Hoàng Đức | Recursive, 700 ký tự | 7 | Cân bằng số chunk (27) và ngữ cảnh; trả lời đầy đủ Q4–Q5. | Q1, Q3 chỉ lấy phần đầu chunk; Q2 thiếu mốc xử lý 3–5 ngày. |
| Hoàng Đức Minh | Recursive, 700 ký tự | Chưa chấm* | Top-3 liên quan ở 5/5 câu; top-1 đúng `doc_id` mục tiêu ở cả 5 câu. | 150 chunks nên không so sánh trực tiếp với run 27 chunks; Q2 thiếu mốc 3–5 ngày, Q4 chưa đủ chi tiết. |
| Tứ | Fixed, 700 ký tự, overlap 70 | 6 | Ít chunk nhất (25), cấu hình đơn giản, có overlap. | Có thể cắt giữa tiêu đề/bước; câu trả lời còn thiếu chi tiết ở nhiều câu. |
| Huy | Sentence, 3 câu/chunk | 7 | Giữ ranh giới câu; trả lời đầy đủ Q1 và Q3. | Nhiều chunk nhất (34); Q4–Q5 dễ lấy heading hơn là chi tiết cần trả lời. |

\* Báo cáo cá nhân tóm tắt mức độ đầy đủ của câu trả lời nhưng không cung cấp toàn văn câu trả lời tác tử cho Q1 và Q3, nên chưa đủ bằng chứng để chấm chính xác theo thang 0–2/câu của nhóm.

#### Đối chiếu run của Hoàng Đức Minh

| # | Top-1 `doc_id` | Score top-1 | Có liên quan trong top-3? | Nhận xét từ báo cáo cá nhân |
| - | -------------- | ----------- | ------------------------- | --------------------------- |
| 1 | `shopee-buyer-return-refund-request` | 0,8498 | Có | Truy xuất đúng hướng dẫn gửi yêu cầu tại trang đơn hàng. |
| 2 | `shopee-buyer-return-refund-request` | 0,8671 | Có | Đúng phần thời gian hoàn tiền; thiếu rõ mốc xử lý 3–5 ngày. |
| 3 | `shopee-buyer-order-cancellation` | 0,8979 | Có | Đúng tài liệu về các trường hợp hủy đơn. |
| 4 | `shopee-buyer-delivery-status-issue` | 0,8743 | Có | Đúng tình huống, nhưng chưa nêu đủ chờ cuộc gọi tiếp theo và 3 lần liên hệ. |
| 5 | `shopee-buyer-delivery-status-issue` | 0,8358 | Có | Đúng lý do “Chưa nhận được hàng” và không cần bằng chứng. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**

Recursive là lựa chọn mặc định tốt nhất cho corpus này vì đạt cùng điểm 7/10 với Sentence nhưng dùng ít chunk hơn (27 so với 34) và giữ được cấu trúc đoạn/dòng của tài liệu chính sách. Tuy vậy, kết quả chưa tạo ra người thắng tuyệt đối: Sentence tốt hơn ở câu hỏi theo bước hoặc trạng thái, còn Recursive tốt hơn khi câu trả lời nằm trong một tình huống giao hàng dài. Vì thế cần chọn theo kiểu câu hỏi, đồng thời cải thiện bước tạo câu trả lời thay vì chỉ thay chunker.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; câu 5 được chạy cả baseline và `metadata_filter={"audience": "buyer"}` để kiểm tra luồng lọc metadata.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
| - | --------------- | ------------------------------- | ------------------------- |
| 1 | Người mua gửi yêu cầu Trả hàng/Hoàn tiền trực tiếp tại trang đơn hàng như thế nào? | Vào **Tôi** → **Chờ giao hàng/Đã giao**, chọn đơn và bấm **Trả hàng/Hoàn tiền**. | `shopee-buyer-return-refund-request` — mục “Cách 1”, bước 1–2. |
| 2 | Yêu cầu Trả hàng/Hoàn tiền thường được xử lý trong bao lâu và tiền hoàn được nhận sau bao lâu nếu yêu cầu được chấp nhận? | Xử lý trong 3–5 ngày làm việc; tiền hoàn về trong 1–14 ngày làm việc tùy phương thức thanh toán. | `shopee-buyer-return-refund-request` — mục “Lưu ý: Thời gian xử lý/Thời gian hoàn tiền”. |
| 3 | Người mua có thể yêu cầu hủy đơn ở những trạng thái nào? | **Chờ xác nhận** hủy ngay; **Chờ lấy hàng** chờ phản hồi Người bán; trạng thái khác không thể yêu cầu hủy. | `shopee-buyer-order-cancellation` — mục 1, bảng trạng thái hủy đơn. |
| 4 | Nếu Shipper không liên hệ nhưng cập nhật giao hàng không thành công, Người mua cần làm gì? | Chờ cuộc gọi tiếp theo; Shipper có 3 lần liên hệ theo thời gian dự kiến. | `shopee-buyer-delivery-status-issue` — tình huống 1. |
| 5 | Nếu quá 24 giờ đơn bị cập nhật đã giao nhưng Người mua chưa nhận được hàng, cần chọn lý do Trả hàng/Hoàn tiền nào và có cần bằng chứng không? | Chọn **Chưa nhận được hàng**; không cần cung cấp bằng chứng. | `shopee-buyer-delivery-status-issue` — tình huống 3. |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm theo `docs/SCORING.md`: 2 điểm/câu khi top-3 chứa chunk liên quan và tác tử trả lời đúng; 1 điểm khi có evidence nhưng câu trả lời thiếu chi tiết; 0 điểm khi không có evidence trong top-3.

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
| - | ------- | ------------------------------- | ------------------------------- | ------- |
| 1 | Gửi yêu cầu Trả hàng/Hoàn tiền tại trang đơn | Sentence | Có, 3/3 chiến lược | Sentence trả lời đủ các bước chính; các chiến lược khác thiên về heading/phần mở đầu. |
| 2 | Thời gian xử lý và hoàn tiền | Đồng hạng | Có, 3/3 chiến lược | Cả ba truy xuất được nguồn nhưng câu trả lời hiện có thiếu mốc 3–5 ngày, nên chỉ đạt 1/2. |
| 3 | Trạng thái có thể hủy đơn | Sentence | Có, 3/3 chiến lược | Sentence giữ được bảng điều kiện và hành động mạch lạc hơn. |
| 4 | Shipper không liên hệ | Recursive | Có, 3/3 chiến lược | Recursive đưa được hướng dẫn chờ liên hệ tiếp và mốc 3 lần vào câu trả lời. |
| 5 | Đã giao quá 24 giờ nhưng chưa nhận | Recursive | Có, 3/3 chiến lược | Recursive trả lời đủ lý do “Chưa nhận được hàng” và yêu cầu về bằng chứng. |

Tổng hợp theo artifact: Đức (Recursive) 7/10, Tứ (Fixed) 6/10 và Huy (Sentence) 7/10. Như vậy 5/5 câu đều có evidence trong top-3, nhưng chất lượng câu trả lời chưa tương ứng hoàn toàn do hàm trả lời trích xuất vài câu đầu của context. Kết quả của Tứ và Huy được suy diễn từ benchmark chung để giữ nhất quán với số chunk, điểm tổng và nhận xét so sánh.

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**

Câu 5 đã chạy cả `search(...)` và `search_with_filter(..., {"audience": "buyer"})`; hai danh sách top-3 giống nhau ở cả ba chiến lược. Lý do là toàn bộ 5 tài liệu hiện đều có `audience: buyer`, nên filter xác minh được luồng kỹ thuật nhưng chưa thu hẹp tập ứng viên để tăng precision. Khi mở rộng corpus bằng tài liệu cho người bán hoặc nhân viên hỗ trợ, filter `audience` và `department` sẽ có giá trị phân biệt rõ hơn.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**

- Cùng một corpus và embedding, cả ba chiến lược đều đưa evidence đúng vào top-3 cho 5/5 câu, nhưng mức độ đầy đủ của câu trả lời khác nhau.
- Recursive và Sentence cùng đạt 7/10; Recursive tạo 27 chunk, ít hơn Sentence (34), còn Fixed tạo ít nhất 25 chunk nhưng chỉ đạt 6/10.
- Metadata filter hoạt động đúng về mặt kỹ thuật nhưng chưa nâng chất lượng vì corpus đồng nhất `audience: buyer`; đây là một giới hạn dữ liệu cần nêu trong demo.

**Bài học rút ra khi so sánh trong nhóm:**

Cùng tài liệu không bảo đảm kết quả cuối giống nhau: vị trí ranh giới chunk quyết định việc chi tiết cần thiết có nằm trong context đầu hay không. Trong thử nghiệm này, truy xuất đúng tài liệu nguồn chưa đủ; câu trả lời trích xuất vẫn có thể bỏ sót mốc thời gian hoặc điều kiện nằm sau vài câu đầu. Vì vậy cần đánh giá cả top-k evidence lẫn câu trả lời cuối.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**

Nhóm sẽ bổ sung tài liệu có `audience` và `department` khác nhau để đo được lợi ích thực của metadata filter, thay vì chỉ kiểm tra API. Với các bài chính sách có bảng và danh sách, nhóm cũng sẽ thêm heading/section vào metadata hoặc áp dụng chunking theo đề mục, giúp giữ nguyên quan hệ giữa điều kiện, trạng thái và hành động. Cuối cùng, bước tạo câu trả lời nên ưu tiên câu chứa thực thể/mốc thời gian của query thay vì luôn lấy các câu đầu context.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
| -------- | ---------------- |
| Lựa chọn tài liệu (Document Set Quality) | 9 / 10 |
| Thiết kế chiến lược (Strategy Design) | 13 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 7 / 10 |
| Thuyết trình (Demo) | 4 / 5 |
| **Tổng phần nhóm** | **33 / 40** |

> Điểm tự đánh giá phản ánh bằng chứng hiện có trong repository. Kết quả của Tứ và Huy là số liệu suy diễn từ benchmark chung; cần thay bằng kết quả chạy cá nhân khi có báo cáo tương ứng.
