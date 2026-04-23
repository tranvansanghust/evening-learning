"""
Seed a temporary test course with lessons and pre-generated Markdown content.
Run: cd backend && source eveninig-learning-venv/bin/activate && python scripts/seed_test_course.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.course import Course
from app.models.lesson import Lesson

COURSE_NAME = "[TEST] Python Web App Cơ Bản"

LESSONS = [
    {
        "sequence_number": 1,
        "title": "Python là gì và tại sao học Python?",
        "content_markdown": """## Python là gì và tại sao học Python?

Python là ngôn ngữ lập trình bậc cao, dễ đọc và dễ học. Ra đời năm 1991, hiện là một trong những ngôn ngữ phổ biến nhất thế giới.

### Tại sao nên học Python?

- **Cú pháp đơn giản** — gần giống tiếng Anh tự nhiên, ít boilerplate hơn Java hay C++
- **Đa dụng** — web backend, data science, AI/ML, automation, scripting
- **Cộng đồng lớn** — hàng triệu thư viện trên PyPI, dễ tìm tài liệu

### Python dùng làm gì?

| Lĩnh vực | Tool phổ biến |
|---|---|
| Web backend | Django, FastAPI, Flask |
| Data science | Pandas, NumPy |
| AI/ML | TensorFlow, PyTorch |
| Automation | Selenium, requests |

### Ví dụ thực tế

```python
# In ra "Xin chào thế giới" — chỉ 1 dòng
print("Xin chào thế giới!")

# Tính tổng 1 đến 100
total = sum(range(1, 101))
print(f"Tổng = {total}")  # Kết quả: 5050
```

### 3 điểm cần nhớ

1. Python dùng **indentation** (thụt đầu dòng) thay vì `{}` để phân chia khối code
2. Không cần khai báo kiểu biến — Python tự suy luận
3. Cài đặt thư viện bằng `pip install <tên-thư-viện>`
""",
    },
    {
        "sequence_number": 2,
        "title": "Biến, kiểu dữ liệu và toán tử",
        "content_markdown": """## Biến, kiểu dữ liệu và toán tử

Biến là "hộp chứa" dữ liệu. Trong Python, bạn không cần khai báo kiểu — Python tự xác định.

### Các kiểu dữ liệu cơ bản

```python
name = "Sang"          # str — chuỗi ký tự
age = 25               # int — số nguyên
height = 1.75          # float — số thực
is_student = True      # bool — True / False
```

### Toán tử số học

```python
a, b = 10, 3

print(a + b)   # 13 — cộng
print(a - b)   # 7  — trừ
print(a * b)   # 30 — nhân
print(a / b)   # 3.333... — chia (luôn trả float)
print(a // b)  # 3  — chia lấy phần nguyên
print(a % b)   # 1  — chia lấy dư
print(a ** b)  # 1000 — lũy thừa
```

### f-string — cách in biến đẹp nhất

```python
name = "Sang"
age = 25
print(f"Tôi là {name}, {age} tuổi")
# → Tôi là Sang, 25 tuổi
```

### 3 điểm cần nhớ

1. Tên biến viết thường, dùng `snake_case` (ví dụ: `my_name`, `total_price`)
2. `=` là phép gán, `==` là phép so sánh bằng
3. `type(x)` trả về kiểu dữ liệu của biến `x`
""",
    },
    {
        "sequence_number": 3,
        "title": "Câu lệnh điều kiện if/else",
        "content_markdown": """## Câu lệnh điều kiện if/else

Điều kiện giúp chương trình đưa ra quyết định khác nhau tùy tình huống.

### Cú pháp cơ bản

```python
age = 18

if age >= 18:
    print("Bạn đủ tuổi trưởng thành")
elif age >= 13:
    print("Bạn đang ở tuổi thiếu niên")
else:
    print("Bạn còn nhỏ")
```

> **Lưu ý:** Python dùng **indentation 4 spaces** để xác định khối lệnh — không có `{}` như Java/C.

### Toán tử so sánh

```python
x = 10
print(x > 5)    # True
print(x == 10)  # True
print(x != 7)   # True
print(x <= 10)  # True
```

### Toán tử logic

```python
age = 20
has_id = True

if age >= 18 and has_id:
    print("Được vào")

if age < 18 or not has_id:
    print("Không được vào")
```

### Ví dụ thực tế — kiểm tra điểm thi

```python
score = 75

if score >= 90:
    grade = "A"
elif score >= 75:
    grade = "B"
elif score >= 60:
    grade = "C"
else:
    grade = "F"

print(f"Điểm: {score} → Xếp loại: {grade}")
# → Điểm: 75 → Xếp loại: B
```

### 3 điểm cần nhớ

1. `if`, `elif`, `else` — không có `switch/case` trong Python (từ Python 3.10 có `match`)
2. Không được thiếu dấu `:` sau điều kiện
3. Điều kiện không cần dấu `()` bao quanh (nhưng vẫn hợp lệ nếu có)
""",
    },
    {
        "sequence_number": 4,
        "title": "Vòng lặp for và while",
        "content_markdown": """## Vòng lặp for và while

Vòng lặp cho phép thực hiện một đoạn code nhiều lần mà không cần copy-paste.

### Vòng lặp `for`

```python
# Lặp qua danh sách
fruits = ["táo", "cam", "xoài"]
for fruit in fruits:
    print(fruit)

# Lặp theo số lần với range()
for i in range(5):       # 0, 1, 2, 3, 4
    print(i)

for i in range(1, 6):    # 1, 2, 3, 4, 5
    print(i)

for i in range(0, 10, 2):  # 0, 2, 4, 6, 8
    print(i)
```

### Vòng lặp `while`

```python
count = 0
while count < 5:
    print(f"Đếm: {count}")
    count += 1
```

> Cẩn thận với vòng lặp vô tận! Luôn đảm bảo có điều kiện thoát.

### `break` và `continue`

```python
for i in range(10):
    if i == 3:
        continue    # bỏ qua i=3, tiếp tục vòng lặp
    if i == 7:
        break       # dừng hẳn vòng lặp
    print(i)
# In ra: 0 1 2 4 5 6
```

### Ví dụ thực tế — tính tổng các số chẵn

```python
total = 0
for n in range(1, 101):
    if n % 2 == 0:
        total += n

print(f"Tổng các số chẵn từ 1-100: {total}")  # 2550
```

### 3 điểm cần nhớ

1. `for` dùng khi biết trước số lần lặp, `while` dùng khi lặp đến khi điều kiện thỏa mãn
2. `enumerate(list)` cho cả index và giá trị: `for i, v in enumerate(fruits)`
3. `range(n)` tạo dãy từ 0 đến n-1, **không bao gồm n**
""",
    },
    {
        "sequence_number": 5,
        "title": "Hàm (Function) trong Python",
        "content_markdown": """## Hàm (Function) trong Python

Hàm là khối code có thể tái sử dụng, giúp tránh lặp code và chia bài toán thành các phần nhỏ.

### Định nghĩa và gọi hàm

```python
def greet(name):
    return f"Xin chào, {name}!"

message = greet("Sang")
print(message)  # Xin chào, Sang!
```

### Tham số mặc định

```python
def greet(name, greeting="Xin chào"):
    return f"{greeting}, {name}!"

print(greet("Sang"))              # Xin chào, Sang!
print(greet("Sang", "Chào mừng"))  # Chào mừng, Sang!
```

### Hàm trả nhiều giá trị

```python
def min_max(numbers):
    return min(numbers), max(numbers)

lo, hi = min_max([3, 1, 4, 1, 5, 9])
print(f"Min: {lo}, Max: {hi}")  # Min: 1, Max: 9
```

### Ví dụ thực tế — tính BMI

```python
def calculate_bmi(weight_kg, height_m):
    bmi = weight_kg / (height_m ** 2)
    if bmi < 18.5:
        status = "Thiếu cân"
    elif bmi < 25:
        status = "Bình thường"
    elif bmi < 30:
        status = "Thừa cân"
    else:
        status = "Béo phì"
    return round(bmi, 1), status

bmi, status = calculate_bmi(70, 1.75)
print(f"BMI: {bmi} — {status}")  # BMI: 22.9 — Bình thường
```

### 3 điểm cần nhớ

1. Hàm không có `return` tự động trả về `None`
2. Đặt tham số có giá trị mặc định **sau** các tham số bắt buộc
3. Tên hàm dùng `snake_case`, mô tả hành động (ví dụ: `calculate_bmi`, `get_user`)
""",
    },
]


def seed():
    db = SessionLocal()
    try:
        # Xóa course test cũ nếu có
        old = db.query(Course).filter(Course.name == COURSE_NAME).first()
        if old:
            db.delete(old)
            db.commit()
            print(f"Đã xóa course cũ: {COURSE_NAME}")

        # Tạo course mới
        course = Course(
            name=COURSE_NAME,
            description="Course tạm thời để test frontend. Có thể xóa sau khi test xong.",
            source="internal",
            total_lessons=len(LESSONS),
        )
        db.add(course)
        db.flush()

        # Tạo lessons
        for data in LESSONS:
            lesson = Lesson(
                course_id=course.course_id,
                sequence_number=data["sequence_number"],
                title=data["title"],
                content_markdown=data["content_markdown"],
            )
            db.add(lesson)

        db.commit()
        db.refresh(course)

        print(f"\n✅ Tạo thành công!")
        print(f"   Course ID : {course.course_id}")
        print(f"   Course    : {course.name}")
        print(f"   Lessons   : {len(LESSONS)} bài")
        print()

        lessons = db.query(Lesson).filter(Lesson.course_id == course.course_id).order_by(Lesson.sequence_number).all()
        for l in lessons:
            print(f"   Bài {l.sequence_number}: lesson_id={l.lesson_id} — {l.title}")

        print()
        print("👉 Test FE tại: http://localhost:5173/lesson/<lesson_id>")
        print(f"   Ví dụ: http://localhost:5173/lesson/{lessons[0].lesson_id}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
