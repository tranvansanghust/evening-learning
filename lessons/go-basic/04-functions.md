# Bài 4 — Functions (Hàm)

**Nguồn:** https://go.dev/tour/basics/4

## Lý thuyết

Hàm trong Go có thể nhận **không hoặc nhiều tham số**. Kiểu dữ liệu viết **sau** tên biến (khác C/Java).

Khi nhiều tham số liên tiếp có cùng kiểu, có thể viết gọn — chỉ ghi kiểu 1 lần ở cuối.

## Ví dụ

```go
package main

import "fmt"

func add(x int, y int) int {
    return x + y
}

// Gọn hơn: cùng kiểu int
func add2(x, y int) int {
    return x + y
}

func main() {
    fmt.Println(add(42, 13))
}
```

## Điểm cần nhớ

- Cú pháp: `func tênHàm(tham số kiểu) kiểuTrảVề { ... }`
- Kiểu viết **sau** tên biến: `x int` không phải `int x`
- Nếu nhiều param cùng kiểu: `x, y int` thay vì `x int, y int`
- Kiểu trả về viết **sau** danh sách tham số
