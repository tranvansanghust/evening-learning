# Bài 3 — Exported Names (Tên xuất)

**Nguồn:** https://go.dev/tour/basics/3

## Lý thuyết

Trong Go, một tên (hàm, biến, hằng, kiểu) được **exported** (công khai ra ngoài package) khi nó bắt đầu bằng **chữ cái in hoa**.

- `Pi` → exported (có thể dùng từ package khác)
- `pi` → unexported (chỉ dùng trong nội bộ package)

Khi import một package, bạn chỉ có thể truy cập các tên exported.

## Ví dụ

```go
package main

import (
    "fmt"
    "math"
)

func main() {
    fmt.Println(math.Pi)  // OK — Pi viết hoa
    // fmt.Println(math.pi) // Lỗi — pi viết thường không exported
}
```

## Điểm cần nhớ

- **Chữ hoa = public**, chữ thường = private (trong package)
- Đây là cơ chế visibility duy nhất của Go — không có `public`/`private` keyword
- Áp dụng cho hàm, biến, struct field, method, hằng số, kiểu dữ liệu
