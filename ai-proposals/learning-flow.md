# Learning Flow

## Mục tiêu

Sau khi onboarding xong, user có thể:
1. Gõ `/today` → xem bài học hiện tại của course đang học
2. Gõ `/done` → kể học được gì → bot tạo quiz
3. Trả lời quiz → nhận feedback → xem tổng kết

---

## Vấn đề hiện tại cần fix trước

### 1. `course_input` step không lưu course info
Trong `_handle_onboarding_step`, bước `course_input` gọi `detect_course_from_input(text)` nhưng **bỏ qua kết quả** — không lưu vào `OnboardingState.course_id` hay đâu cả.

### 2. `complete_onboarding` chỉ xoá state, không tạo Course/UserCourse
Sau khi onboarding xong, không có `Course` hay `UserCourse` nào được tạo → không biết user học course nào, bài nào.

### 3. `/today` và `/done` handler chỉ trả lời tĩnh
Chưa kết nối với DB để lấy course/lesson thực tế, chưa kết nối với `QuizService.start_quiz`.

---

## Các file cần thay đổi / tạo mới

| File | Loại | Thay đổi |
|------|------|----------|
| `app/routers/telegram_handlers.py` | sửa | Fix `course_input` step, implement `/today`, implement `/done`, implement `_handle_checkin` |
| `app/services/onboarding_service.py` | sửa | `complete_onboarding` tạo Course + UserCourse, thêm field `course_topic` vào state |
| `app/models/onboarding_state.py` | sửa | Thêm column `course_topic` (String) để lưu topic/URL tạm |
| `backend/alembic/versions/` | tạo mới | Migration thêm `course_topic` column |

---

## Kế hoạch thực hiện (từng bước)

### Bước 1 — Thêm `course_topic` vào `OnboardingState`
- Thêm column `course_topic = Column(String(500), nullable=True)` vào model
- Tạo alembic migration

### Bước 2 — Lưu course info khi user nhập ở `course_input` step
- Trong `_handle_onboarding_step`, sau `detect_course_from_input(text)`:
  - Lưu `course_topic=text` vào `OnboardingState`

### Bước 3 — `complete_onboarding` tạo Course + UserCourse + Lesson
- Đọc `ob_state.course_topic` và `q1_answer`, `q2_answer`, `deadline`, `hours_per_day`
- `assess_level(q1, q2)` → cập nhật `user.level`
- `create_course_from_curriculum(name, slug, curriculum)` → tạo Course + Lessons
- `save_user_course_enrollment(user_id, course_id)` → tạo UserCourse
- Trả về first lesson để gửi ngay cho user

### Bước 4 — Implement `/today` handler
Hiển thị bài học hiện tại của user:

```
/today
 └─ lookup user → get UserCourse (status=IN_PROGRESS)
 └─ nếu không có UserCourse → "Bạn chưa có khoá học, dùng /start"
 └─ lấy current lesson (lesson tiếp theo chưa completed)
 └─ gửi thông tin: tên course, tên lesson, mô tả, thời lượng
 └─ gợi ý: "Học xong thì gõ /done nhé!"
```

Query để lấy current lesson:
- `UserCourse` với `user_id` + `status=IN_PROGRESS`
- Lấy lesson đầu tiên của course theo `sequence_number` (MVP: luôn lesson 1)

### Bước 5 — Implement `/done` handler (2 sub-states)
Handler `/done` cần check xem user đang ở giai đoạn nào:
- **Chưa có quiz session**: hỏi "hôm nay bạn học được gì?" → lưu vào temporary state (dùng `QuizSession.messages` hoặc field mới)
- **Đang trong quiz**: không làm gì (đã có `handle_text` xử lý)

Flow chi tiết:
```
/done
 └─ lookup user → get current UserCourse → get current lesson
 └─ nếu có active QuizSession → "bạn đang làm quiz rồi"
 └─ nếu không → "hôm nay bạn học được gì?" + set state "checkin"
      └─ user trả lời text
           └─ handle_text nhận ra state "checkin"
           └─ QuizService.start_quiz(user_id, lesson_id, user_checkin=text)
           └─ gửi first_question
```

### Bước 6 — Thêm state `checkin` vào `handle_text` routing
Trong `_handle_onboarding_step` hoặc tạo hàm `_handle_checkin` riêng:
- State `checkin`: nhận text → gọi `start_quiz` → gửi câu hỏi đầu tiên

### Bước 7 — Hoàn thiện quiz end flow
Khi `next_action == "end"` trong `_handle_quiz_answer`:
- Gửi summary
- Cập nhật `UserCourse` lesson progress (optional cho MVP)
- Gợi ý `/done` cho bài tiếp theo

---

## Giải thích thiết kế

**Tại sao dùng `OnboardingState.course_topic` thay vì tạo Course ngay lúc `course_input`?**
- User chưa trả lời Q1/Q2 → chưa biết level → chưa biết curriculum cần tạo như thế nào
- Tạo Course sau khi có đủ thông tin (level, deadline, hours) giúp tạo đúng curriculum

**Tại sao dùng `current_step="checkin"` trong `OnboardingState`?**
- Tận dụng cơ chế routing đã có trong `handle_text` (`ob_state.current_step`)
- Thay vì tạo bảng/state mới, tái sử dụng `OnboardingState` như một "conversation state" chung
- Sau khi quiz bắt đầu, `OnboardingState` bị xóa (hoặc step chuyển sang idle)

**Dependency giữa các bước:**
- Bước 1 → 2 → 3 phải theo thứ tự (migration trước, rồi mới sửa code)
- Bước 4, 5, 6 độc lập nhau nhưng 5 cần 4 xong trước
