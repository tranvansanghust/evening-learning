# System Core Features & Use Cases

> Tài liệu này tổng hợp các tính năng cốt lõi và use case tương ứng đã được thống nhất.
> Version: 0.1 — Draft

---

## Tổng quan hệ thống

Ứng dụng học tập hoạt động chủ yếu qua **Telegram Bot**, giúp người dùng học có hệ thống, biết mình thực sự đang tiến bộ đến đâu — mà không cần mở thêm ứng dụng nào khác.

**Tagline:** *Học có hệ thống, biết mình đang ở đâu, không cần mở app.*

---

## Feature 1 — Knowledge Tracker

### Mô tả
Theo dõi những gì user **thực sự hiểu và nhớ**, không phải chỉ những gì đã xem hay đã học qua. Không dùng streak.

### Use Cases

| # | Use Case | Mô tả |
|---|---|---|
| 1.1 | Xem danh sách concepts đã học | User xem được toàn bộ các concept đã học, phân theo topic/chủ đề |
| 1.2 | Xem điểm yếu | Hệ thống highlight những concept user hay trả lời sai trong quiz |
| 1.3 | Xem progress theo topic | Progress được đo theo từng chủ đề, không phải theo ngày |
| 1.4 | Xem retention rate | Sau mỗi quiz, user thấy tỉ lệ nhớ được so với lần trước |

### Nguyên tắc thiết kế
- "Watched" ≠ "Learned" — chỉ tính concept là đã học khi user giải thích lại được
- Không dùng streak, không tạo streak anxiety
- Đo chất lượng, không đo số ngày

---

## Feature 2 — Learn & Test Loop

### Mô tả
Vòng lặp học tập cốt lõi: user học → giải thích lại bằng lời của mình → AI lưu lại → AI quiz sau 3 ngày → user thấy mình retain được gì.

### Use Cases

| # | Use Case | Mô tả |
|---|---|---|
| 2.1 | User báo học xong | User báo "xong rồi" sau khi học một section |
| 2.2 | Giải thích lại concept | Bot hỏi user giải thích lại concept vừa học bằng lời của mình (Feynman Technique) |
| 2.3 | AI lưu và phân tích | Hệ thống lưu lại giải thích, phân tích điểm hiểu đúng và chỗ còn mơ hồ |
| 2.4 | Nhận quiz sau 3 ngày | Sau 3 ngày, bot gửi quiz dựa trên chính những gì user đã giải thích |
| 2.5 | Xem kết quả quiz | User thấy mình nhớ được bao nhiêu % concepts đã học |

### Nguyên tắc thiết kế
- Quiz được sinh ra từ **lời giải thích của chính user**, không phải từ nội dung generic
- Ưu tiên đo retention thực tế, không phải khả năng nhận dạng đáp án
- Tần suất quiz: spaced repetition — ngày 3, ngày 7, ngày 14 sau khi học

---

## Feature 3 — Curriculum Builder

### Mô tả
Hệ thống tự động tạo lộ trình học cá nhân hoá dựa trên input của user: khoá học/topic muốn học, deadline, số giờ mỗi ngày, và trình độ hiện tại.

### Use Cases

| # | Use Case | Mô tả |
|---|---|---|
| 3.1 | Tạo lộ trình từ Udemy course | User nhập URL → hệ thống fetch curriculum → sinh lịch học theo ngày |
| 3.2 | Tạo lộ trình từ topic | User nhập topic → hệ thống xác định level → sinh lộ trình phù hợp |
| 3.3 | Điều chỉnh lộ trình khi trễ | Khi user bỏ lỡ nhiều ngày, hệ thống tự reschedule lại |
| 3.4 | User chủ động reschedule | User có thể yêu cầu thay đổi lịch học bất cứ lúc nào |
| 3.5 | Lộ trình theo level | Level 0 → bắt đầu từ nền tảng cơ bản nhất; Level 3 → bỏ qua phần đã biết |

### Input cần thiết
- Khoá học / Topic muốn học
- Deadline hoàn thành
- Số giờ học được mỗi ngày
- Giờ muốn được nhắc
- Trình độ hiện tại (Level 0–3, xác định qua onboarding)

---

## Feature 4 — Telegram-first Interface

### Mô tả
Toàn bộ tương tác của user với hệ thống diễn ra qua Telegram Bot. Không cần mở app riêng. Đây là **killer feature** tạo ra sự khác biệt — giảm friction xuống gần bằng 0.

### Use Cases

| # | Use Case | Mô tả |
|---|---|---|
| 4.1 | Onboarding qua bot | Toàn bộ quá trình đăng ký và thiết lập học qua chat |
| 4.2 | Nhận nhắc học hàng ngày | Bot tự động nhắc đúng giờ user đã chọn |
| 4.3 | Báo cáo học xong | User báo "xong" và giải thích concept ngay trong chat |
| 4.4 | Nhận và trả lời quiz | Quiz được gửi qua bot, user trả lời bằng inline buttons hoặc text |
| 4.5 | Xem progress | User gõ lệnh để xem knowledge tracker ngay trong chat |
| 4.6 | Re-engagement | Bot nhắc lại tại checkpoint +1, +3, +5 ngày khi user bỏ học |

### Bot Commands (dự kiến)
```
/start      — Bắt đầu onboarding
/today      — Xem bài học hôm nay
/done       — Báo học xong, bắt đầu explain session
/progress   — Xem knowledge tracker
/quiz       — Làm quiz ngay
/reschedule — Điều chỉnh lịch học
/pause      — Tạm dừng nhắc nhở
```

---

## Re-engagement Flow

Khi user bấm "Hôm nay bận" hoặc không phản hồi:

| Thời điểm | Hành động của Bot |
|---|---|
| +1 ngày | Nhắc nhẹ: "Hôm qua bạn bận, hôm nay học tiếp nhé?" |
| +3 ngày | Nhắc kèm context: deadline còn bao nhiêu ngày, đang học đến đâu |
| +5 ngày | Hỏi có muốn reschedule không — không nhắc thêm sau đó |
| Sau +5 | Bot im lặng, chờ user chủ động gõ /resume |

---

## Những tính năng để Phase 2

- **Cohort / Group learning:** Kết nối user cùng học một topic vào group Telegram chung
- **Asynchronous learning feed:** User post learning log public, người khác react/comment
- **Pair accountability:** Ghép 2 user cùng cam kết với nhau
- **Bổ sung vào onboard:** Cho user custom thêm về lịch học, có thể học theo tuần, ngày, tháng. Số lần học mỗi chu kỳ, và lịch nhắc theo từng lần.
