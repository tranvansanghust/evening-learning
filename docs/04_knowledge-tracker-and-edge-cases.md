# Knowledge Tracker & Edge Cases

> Tài liệu này mô tả cách hiển thị tiến độ học tập và các trường hợp kết thúc khoá học.
> Version: 0.1 — Draft

---

## Knowledge Tracker View

User gõ `/progress` bất cứ lúc nào để xem tiến độ:

```
Bot:
┌──────────────────────────────────────────┐
│ 📊 Tiến độ học của bạn                   │
│                                          │
│ 📚 Bài học:    12 / 30 bài              │
│ 🧠 Concepts:   34 / 89 concepts          │
└──────────────────────────────────────────┘
```

**Nguyên tắc thiết kế:**
- Hiển thị đúng 2 con số — không cần chart, không cần streak
- Concepts được tính là "đã nắm" khi user trả lời đúng trong oral-test
- Concepts trả lời sai vẫn được tính vào tổng số, chưa tính vào "đã nắm"

---

## Edge Cases — Kết thúc khoá học

### Trạng thái nội bộ

| Trạng thái | Điều kiện |
|---|---|
| PASS | User hoàn thành toàn bộ bài học trong lộ trình |
| FAIL | User bỏ giữa chừng hoặc chủ động đổi sang khoá học khác |

> **Lưu ý:** PASS / FAIL chỉ là trạng thái nội bộ của hệ thống. Ngôn ngữ hiển thị với user luôn trung tính, không dùng từ "fail".

---

### Khi PASS — Hoàn thành khoá học

```
Bot:
┌──────────────────────────────────────────┐
│ 🎉 Xuất sắc! Bạn đã hoàn thành          │
│ "[Tên khoá học]"!                        │
│                                          │
│ Bước tiếp theo bạn muốn chinh phục gì?  │
│                                          │
│  [Option nâng cao 1]                     │
│  [Option nâng cao 2]                     │
│  [Option nâng cao 3]                     │
│  [Tôi muốn học thứ khác...]             │
└──────────────────────────────────────────┘
```

**Logic gợi ý 3 options:**
- Hệ thống tự động gợi ý các khoá học ở level cao hơn, liên quan đến topic vừa học
- Nếu user chọn "Tôi muốn học thứ khác..." → User nhập tự do → Quay lại flow onboarding với topic mới

---

### Khi FAIL — Kết thúc giữa chừng

```
Bot:
┌──────────────────────────────────────────┐
│ Không sao cả! Đôi khi thay đổi hướng    │
│ là lựa chọn đúng đắn nhất 💪            │
│                                          │
│ Lúc này bạn đang hứng thú với           │
│ chủ đề nào?                              │
└──────────────────────────────────────────┘

User trả lời tự do
        ↓
→ Quay lại flow onboarding với topic mới
```

**Điểm khác biệt so với PASS:**
- PASS: Gợi ý có định hướng (3 options liên quan đến topic cũ)
- FAIL: Hỏi mở để user tự xác định hướng đi mới — không giả định user muốn học gì tiếp

---

## Những gì chưa được thiết kế (sẽ bàn tiếp)

- **Spaced repetition logic:** Khi nào bot hỏi lại concept nào — để quyết định sau ở phần kỹ thuật
