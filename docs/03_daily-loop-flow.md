# Daily Loop Flow

> Tài liệu này mô tả vòng lặp học tập hàng ngày sau khi user đã hoàn thành onboarding.
> Version: 0.1 — Draft

---

## Tổng quan

Daily Loop gồm 3 giai đoạn chính:

```
1. NHẮC HỌC      →      2. HỌC      →      3. KIỂM TRA & TỔNG HỢP
(Bot remind)          (User học)           (Oral-test + Summary)
```

Có 2 track học tập khác nhau, xử lý khác nhau:
- **Track A:** User học trên hệ thống ngoài (Udemy, sách,...)
- **Track B:** User học nội dung do hệ thống cung cấp

---

## Giai đoạn 1 — Nhắc học

```
Đến giờ nhắc đã cài
        ↓
Bot:
┌──────────────────────────────────────────┐
│ 🔔 Đến giờ học rồi!                      │
│                                          │
│ Hôm nay: [Tên bài học / Section]         │
│ Dự kiến: ~[X] phút                       │
│                                          │
│  [Bắt đầu học 🚀]      [Hôm nay bận ⏭]  │
└──────────────────────────────────────────┘
```

**Nếu user bấm "Hôm nay bận":**

| Thời điểm | Hành động |
|---|---|
| +1 ngày | Nhắc nhẹ: "Hôm qua bạn bận, hôm nay học tiếp nhé?" |
| +3 ngày | Nhắc kèm context: deadline còn bao nhiêu ngày, đang ở đâu |
| +5 ngày | Hỏi có muốn reschedule không — dừng nhắc sau đó |
| Sau +5 | Bot im lặng, chờ user gõ /resume |

---

## Giai đoạn 2 — Học

### Track A — External Learning (Udemy, sách,...)

```
User bấm [Bắt đầu học 🚀]
        ↓
Bot ghi nhận timestamp bắt đầu
Bot: "Bắt đầu thôi! Mình chờ bạn học xong nhé 💪"
        ↓
User sang Udemy / mở sách học
        ↓
User quay lại bot, gõ /done hoặc bấm [Học xong ✅]
        ↓
→ Chuyển sang Giai đoạn 3
```

### Track B — Internal Learning (Nội dung hệ thống)

```
Bot gửi link bài học kèm nhắc:
┌──────────────────────────────────────────┐
│ 📖 Bài hôm nay:                          │
│ [Tên bài học]                            │
│                                          │
│ 👉 [Mở bài học]                          │
└──────────────────────────────────────────┘
        ↓
User click link → Đọc bài (text content)
        ↓
Cuối bài: User bấm [Hoàn thành ✅]
        ↓
Bot:
┌──────────────────────────────────────────┐
│ 🎉 Bạn vừa hoàn thành                   │
│ "[Tên bài học]"!                         │
│                                          │
│ Cùng nhìn lại xem bạn đã nắm được       │
│ những gì trong bài học này nhé 💡        │
│                                          │
│  [Bắt đầu kiểm tra 🚀]                  │
└──────────────────────────────────────────┘
        ↓
User bấm [Bắt đầu kiểm tra 🚀]
        ↓
→ Chuyển sang Giai đoạn 3
```

---

## Giai đoạn 3 — Kiểm tra & Tổng hợp

### Bước 3.1 — Check-in

**Track A và Track B xử lý khác nhau tại bước này:**

- **Track B (Internal):** Bot đã biết chính xác nội dung bài học → gửi lời chúc mừng + chờ user sẵn sàng → user bấm [Bắt đầu] → gen câu hỏi đầu tiên.
- **Track A (External):** Bot chưa biết user thực sự học gì → cần hỏi trước khi gen quiz.

Trước khi vào quiz, bot hỏi user học được gì — vừa để user nhớ lại, vừa để bot có context gen câu hỏi đúng trọng tâm:

```
Bot:
┌──────────────────────────────────────────┐
│ Tốt lắm! Hôm nay bạn học đến đâu rồi?   │
│ Kể mình nghe bạn tiếp thu được gì nào!  │
└──────────────────────────────────────────┘

User: "Học xong Section 3 về useState,
       hiểu cách dùng cơ bản nhưng chưa
       rõ khi nào dùng useReducer thay thế"
        ↓
Bot dùng input này để:
  • Cập nhật tiến độ trong curriculum
  • Gen câu hỏi đúng với nội dung đã học
  • Ghi nhận sẵn điểm user tự nhận là chưa rõ
```

---

### Bước 3.2 — Oral-Test

**Format:** Hội thoại tự nhiên giữa bot và user — không phải trắc nghiệm.

**Số câu hỏi:** Không cố định — bot tự điều chỉnh dựa trên mức độ hào hứng của user.

| Tín hiệu từ user | Hành động của bot |
|---|---|
| Trả lời dài, chi tiết, có ví dụ | Đào sâu hơn, hỏi câu tiếp theo |
| User tự đặt câu hỏi ngược lại | Trả lời + tiếp tục explore |
| Trả lời đúng nhưng ngắn gọn | Hỏi thêm 1 câu probe |
| "Không biết" / trả lời mơ hồ | Ghi nhận, không sửa, chuyển câu tiếp |
| Không phản hồi sau 10 phút | Lưu lại session, kết thúc |

**Quy tắc quan trọng trong lúc quiz:**
- ✅ Ghi nhận câu trả lời sai — lưu vào hệ thống
- ✅ Động viên tự nhiên sau mỗi câu
- ❌ Không sửa sai ngay trong lúc quiz
- ❌ Không gợi ý đáp án đúng

**Ví dụ — Engagement cao:**
```
Bot:  "useState dùng để làm gì?"

User: "Dùng để quản lý state trong
       functional component, mỗi khi
       state thay đổi thì component
       re-render lại. Ví dụ như đếm số
       lần click button."

Bot:  "Giải thích hay đấy! Vậy khi nào
       bạn nên dùng useReducer
       thay vì useState?"

→ Tiếp tục cho đến khi user giảm
  độ chi tiết trong câu trả lời
```

**Ví dụ — Engagement thấp:**
```
Bot:  "useState dùng để làm gì?"

User: "Để quản lý state"

Bot:  "Đúng rồi 👍 Bạn có thể cho
       mình một ví dụ cụ thể không?"

User: "Ví dụ như cái form"

Bot:  "Tốt! Mình ghi nhận rồi nhé.
       Mình sẽ hỏi lại phần này
       sau để chắc chắn bạn nắm chắc hơn."

→ Wrap up sớm
```

---

### Bước 3.3 — Post-Quiz Summary

Sau khi hoàn thành tất cả câu hỏi, bot tổng hợp và gửi summary:

```
Bot:
┌────────────────────────────────────────────────┐
│ 📝 Tóm tắt buổi học — [Tên bài / Section]     │
│ Ngày: [DD/MM/YYYY]                             │
│                                                │
│ ✅ Nắm chắc:                                   │
│ • [Concept 1]                                  │
│ • [Concept 2]                                  │
│                                                │
│ ⚠️  Cần ôn lại:                                │
│ • [Concept A]                                  │
│   → Giải thích đúng: [Nội dung giải thích]    │
│                                                │
│ • [Concept B]                                  │
│   → Giải thích đúng: [Nội dung giải thích]    │
│                                                │
│ 🔁 Mình sẽ hỏi lại sau 3 ngày nhé!            │
│                                                │
│  [Xem lại bất cứ lúc nào: /review useState]   │
└────────────────────────────────────────────────┘
```

**Lưu trữ:**
- Summary được lưu vào hệ thống, không phải file download
- User truy cập lại bất cứ lúc nào qua `/review` hoặc `/review [topic]`
- Đây là raw data cho Knowledge Tracker

---

## Kết nối với Knowledge Tracker

```
Mỗi Post-Quiz Summary
        ↓
Được lưu vào hệ thống theo [topic] + [ngày]
        ↓
Knowledge Tracker tổng hợp lại:
  • Concepts đã nắm chắc theo thời gian
  • Concepts hay sai / cần ôn
  • Retention rate theo từng topic
```

---

## Commands liên quan

```
/done       — Báo học xong, bắt đầu check-in + oral-test
/review     — Xem tất cả post-quiz summaries
/review [topic] — Xem summary theo chủ đề cụ thể
/resume     — Tiếp tục học sau khi đã bỏ lỡ nhiều ngày
```

---

## Những gì chưa được thiết kế (sẽ bàn tiếp)

- Knowledge Tracker View: Trông như thế nào khi user gõ /progress trong Telegram?
- Edge Cases: User muốn thay đổi lộ trình, user hoàn thành khoá học
- Quiz spaced repetition: Logic cụ thể để quyết định khi nào hỏi lại concept nào
