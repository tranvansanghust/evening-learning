# Bài 2 — Imports (Nhập gói)

**Nguồn:** https://go.dev/tour/basics/2

## Lý thuyết

Go dùng cú pháp `import` để nhập các package. Có thể import từng gói riêng lẻ hoặc dùng **"factored" import** (gom vào cặp ngoặc đơn) — đây là style được khuyến nghị.

## Ví dụ

```go
package main

import (
    "fmt"
    "math"
)

func main() {
    fmt.Printf("Now you have %g problems.\n", math.Sqrt(7))
}
```

Import từng dòng (không khuyến nghị):

```go
import "fmt"
import "math"
```

## Điểm cần nhớ

- Ưu tiên dùng **factored import**: `import ( "fmt" "math" )`
- Nếu import một package mà không dùng → **lỗi biên dịch**
- Standard library của Go rất phong phú: `fmt`, `math`, `strings`, `os`, v.v.
