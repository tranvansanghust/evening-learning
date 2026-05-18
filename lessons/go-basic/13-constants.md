# Bài 13 — Constants (Hằng số)

**Nguồn:** https://go.dev/tour/basics/13

## Lý thuyết

Hằng số trong Go dùng từ khoá `const`. Hằng có thể là kiểu character, string, boolean, hoặc số. **Không dùng `:=` với hằng số**.

Hằng số được tính **tại compile time** — không thể là kết quả của hàm runtime.

## Ví dụ

```go
package main

import "fmt"

const Pi = 3.14

func main() {
    const World = "世界"
    fmt.Println("Hello", World)
    fmt.Println("Happy", Pi, "Day")

    const Truth = true
    fmt.Println("Go rules?", Truth)
}
```

Factored const (gom nhiều hằng):

```go
const (
    StatusOK    = 200
    StatusNotFound = 404
)
```

## Điểm cần nhớ

- Khai báo bằng `const`, **không dùng `:=`**
- Hằng số không thể thay đổi sau khi khai báo
- Có thể gom nhiều hằng với `const ( ... )` giống factored import
- Hằng số tính tại compile time — giá trị phải là biểu thức hằng
