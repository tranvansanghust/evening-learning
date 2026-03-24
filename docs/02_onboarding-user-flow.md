# Onboarding User Flow

> Tài liệu này mô tả toàn bộ flow từ lúc user tương tác với Telegram Bot lần đầu tiên.
> Version: 0.1 — Draft

---

## Nguyên tắc thiết kế

- **Cho user thấy giá trị trong vòng 2 phút đầu tiên** — trước khi hỏi quá nhiều
- **Tối đa 4 câu hỏi onboarding** — đủ để cá nhân hoá, không gây friction
- **Inline buttons là UI mặc định** — giảm typing, tăng consistency
- **Lộ trình được sinh ra ngay cuối onboarding** — user thấy kết quả cụ thể tức thì

---

## Step 1 — Khởi động

```
User gõ: /start

Bot:
┌────────────────────────────────────────────┐
│ Chào bạn! Mình là học bạn AI 👋            │
│                                            │
│ Mình giúp bạn học có hệ thống và biết      │
│ mình thực sự đang tiến bộ đến đâu.         │
│                                            │
│ Bạn đang muốn học gì?                      │
│ (paste link Udemy hoặc gõ tên chủ đề)     │
└────────────────────────────────────────────┘
```

---

## Step 2 — Xác định học liệu & đánh giá trình độ

### Nhánh A: User nhập Udemy URL

```
User: https://www.udemy.com/course/react-complete-guide/

Bot:
┌────────────────────────────────────────────┐
│ Tìm thấy: "React - The Complete Guide"     │
│ Tác giả: Maximilian Schwarzmüller          │
│ Level: Beginner → Advanced  |  48 giờ      │
│                                            │
│ Mình sẽ dùng lộ trình của khoá này.        │
│ Đúng khoá bạn muốn học không?              │
│                                            │
│  [Đúng rồi ✅]     [Sai, nhập lại ❌]      │
└────────────────────────────────────────────┘

→ Không cần assessment, chuyển thẳng sang Step 3
```

---

### Nhánh B: User nhập topic chung

```
User: "Tôi muốn học React"

→ Bắt đầu 2-câu hỏi Binary Tree Assessment
```

**Câu hỏi Q1:**
```
Bot:
┌────────────────────────────────────────────┐
│ Bạn đã tự build một web app bằng           │
│ JavaScript chưa?                           │
│                                            │
│  [Chưa bao giờ]      [Rồi]                │
└────────────────────────────────────────────┘
```

**Nếu Q1 = "Chưa bao giờ" → Q2a:**
```
Bot:
┌────────────────────────────────────────────┐
│ Bạn có biết HTML/CSS không?                │
│                                            │
│  [Chưa biết]     [Biết rồi]               │
└────────────────────────────────────────────┘
```

**Nếu Q1 = "Rồi" → Q2b:**
```
Bot:
┌────────────────────────────────────────────┐
│ Bạn đã dùng framework nào khác chưa?       │
│ (Vue, Angular, Svelte,...)                 │
│                                            │
│  [Chưa]      [Dùng rồi]                   │
└────────────────────────────────────────────┘
```

---

### Bảng xác định Level

```
Q1: Chưa + Q2a: Chưa biết   → Level 0: Bắt đầu từ HTML/CSS/JS cơ bản
Q1: Chưa + Q2a: Biết rồi    → Level 1: Sẵn sàng học React từ đầu
Q1: Rồi  + Q2b: Chưa        → Level 2: Học React patterns & ecosystem
Q1: Rồi  + Q2b: Dùng rồi   → Level 3: Tập trung advanced topics
```

> **Nguyên tắc:** Hỏi về hành vi thực tế (đã build chưa, đã dùng chưa)
> thay vì để user tự đánh giá trình độ — tránh Dunning-Kruger effect.

---

## Step 3 — Thu thập thông tin lên lịch

**Câu hỏi về deadline:**
```
Bot:
┌────────────────────────────────────────────┐
│ Bạn muốn hoàn thành khoá học khi nào?      │
│                                            │
│  [1 tháng]  [2 tháng]  [3 tháng]          │
│         hoặc gõ ngày cụ thể               │
└────────────────────────────────────────────┘
```

**Câu hỏi về giờ học mỗi ngày:**
```
Bot:
┌────────────────────────────────────────────┐
│ Mỗi ngày bạn có thể dành bao nhiêu giờ    │
│ để học?                                    │
│                                            │
│  [1 giờ]     [2 giờ]     [3+ giờ]         │
└────────────────────────────────────────────┘
```

**Câu hỏi về giờ nhắc:**
```
Bot:
┌────────────────────────────────────────────┐
│ Bạn muốn mình nhắc học lúc mấy giờ        │
│ mỗi ngày?                                  │
│                                            │
│  [7:00 sáng] [12:00 trưa] [9:00 tối]      │
│          hoặc gõ giờ khác                 │
└────────────────────────────────────────────┘
```

---

## Step 4 — Xác nhận & Sinh lộ trình

```
Bot:
┌──────────────────────────────────────────────┐
│ ✅ Mình đã tạo lộ trình cho bạn!             │
│                                              │
│ 📚 Khoá học : React for Beginners            │
│ 🎯 Trình độ : Level 1 — Biết HTML/CSS        │
│ 🗓 Thời gian: 60 ngày                        │
│ ⏱ Mỗi ngày : ~1 giờ                         │
│ 🔔 Nhắc lúc : 21:00 hàng ngày               │
│                                              │
│ 👉 HÔM NAY bắt đầu với:                      │
│ "Section 1 — Tại sao cần học React?"         │
│ Dự kiến: ~45 phút                            │
│                                              │
│ Sau khi học xong, quay lại đây và            │
│ kể mình nghe bạn hiểu được gì nhé!           │
│                                              │
│  [Bắt đầu học 🚀]                            │
└──────────────────────────────────────────────┘
```

---

## Tóm tắt Flow

```
/start
  │
  ├─ Nhập Udemy URL ──────────────────────────────────┐
  │    └─ Confirm course metadata                     │
  │                                                   │
  └─ Nhập topic                                       │
       └─ Q1: Đã build web app chưa?                  │
            ├─ Chưa → Q2a: Biết HTML/CSS?             │
            │          ├─ Chưa → Level 0              │
            │          └─ Rồi  → Level 1              │
            └─ Rồi  → Q2b: Đã dùng framework?         │
                       ├─ Chưa → Level 2              │
                       └─ Rồi  → Level 3              │
                                                      │
  ←────────────────────────────────────────────────── ┘
  │
  ├─ Hỏi deadline
  ├─ Hỏi giờ/ngày
  ├─ Hỏi giờ nhắc
  │
  └─ Sinh lộ trình cá nhân hoá
       └─ Gửi bài học đầu tiên ngay lập tức ✅
```

---

## Những gì chưa được thiết kế (sẽ bàn tiếp)

- Daily Loop: Sau khi user báo "học xong" → bot xử lý như thế nào?
- Quiz Flow: Sinh khi nào, format ra sao, tần suất thế nào?
- Knowledge Tracker View: User xem progress trông như thế nào trong Telegram?
- Edge Cases: User muốn thay đổi lộ trình, user hoàn thành khoá họcEdg
