# Bài 5 — Multiple Results (Nhiều giá trị trả về)

**Nguồn:** https://go.dev/tour/basics/5

## Lý thuyết

Hàm Go có thể **trả về nhiều giá trị** cùng lúc — đây là tính năng rất phổ biến trong Go, đặc biệt để trả về kết quả kèm lỗi.

## Ví dụ

```go
package main

import "fmt"

func swap(x, y string) (string, string) {
    return y, x
}

func main() {
    a, b := swap("hello", "world")
    fmt.Println(a, b) // world hello
}
```

Ứng dụng thực tế — trả về giá trị và lỗi:

```go
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, fmt.Errorf("chia cho 0")
    }
    return a / b, nil
}
```

## Điểm cần nhớ

- Khai báo nhiều kiểu trả về trong dấu ngoặc: `(string, string)`
- Pattern phổ biến nhất: `(result, error)` — trả về kết quả và lỗi
- Nhận nhiều giá trị: `a, b := swap(...)` hoặc dùng `_` để bỏ qua giá trị không cần
