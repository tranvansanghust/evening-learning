# Bài 14 — Numeric Constants (Hằng số)

**Nguồn:** https://go.dev/tour/basics/14

## Lý thuyết

**Numeric constants** (hằng số) trong Go là **untyped** (không có kiểu cụ thể) cho đến khi được dùng trong context cần kiểu. Điều này cho phép hằng số có **độ chính xác rất cao** — có thể biểu diễn số rất lớn hoặc rất nhỏ mà không bị overflow.

Khi dùng hằng trong biểu thức, Go suy luận kiểu phù hợp từ context.

## Ví dụ

```go
package main

import "fmt"

const (
    // Số rất lớn — hợp lệ vì là untyped constant
    Big   = 1 << 100
    Small = Big >> 99  // = 1 << 1 = 2
)

func needInt(x int) int { return x*10 + 1 }
func needFloat(x float64) float64 { return x * 0.1 }

func main() {
    fmt.Println(needInt(Small))    // 21
    fmt.Println(needFloat(Small))  // 0.2
    fmt.Println(needFloat(Big))    // 1.2676506e+29
    // needInt(Big) → lỗi: Big vượt quá int
}
```

## Điểm cần nhớ

- Numeric constant là **untyped** — nhận kiểu khi được dùng
- Có thể biểu diễn số cực lớn/nhỏ mà không overflow (chỉ ở compile time)
- Khi truyền vào hàm, constant nhận kiểu của tham số — nếu vượt range → lỗi biên dịch
- `iota` là cách tạo hằng số tự tăng trong `const` block (pattern phổ biến cho enum)
