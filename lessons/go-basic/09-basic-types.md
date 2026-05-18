# Bài 9 — Basic Types (Kiểu dữ liệu cơ bản)

**Nguồn:** https://go.dev/tour/basics/9

## Lý thuyết

Go có các kiểu dữ liệu cơ bản sau:

| Nhóm | Kiểu |
|---|---|
| Boolean | `bool` |
| Chuỗi | `string` |
| Số nguyên | `int`, `int8`, `int16`, `int32`, `int64` |
| Số nguyên không dấu | `uint`, `uint8`, `uint16`, `uint32`, `uint64`, `uintptr` |
| Byte / Rune | `byte` (= uint8), `rune` (= int32, Unicode code point) |
| Số thực | `float32`, `float64` |
| Số phức | `complex64`, `complex128` |

Kiểu `int`, `uint`, `uintptr` có kích thước 32 hoặc 64 bit tuỳ nền tảng.

## Ví dụ

```go
package main

import (
    "fmt"
    "math/cmplx"
)

var (
    ToBe   bool       = false
    MaxInt uint64     = 1<<64 - 1
    z      complex128 = cmplx.Sqrt(-5 + 12i)
)

func main() {
    fmt.Printf("Type: %T Value: %v\n", ToBe, ToBe)
    fmt.Printf("Type: %T Value: %v\n", MaxInt, MaxInt)
    fmt.Printf("Type: %T Value: %v\n", z, z)
}
```

## Điểm cần nhớ

- Mặc định dùng `int` cho số nguyên, `float64` cho số thực
- `byte` = `uint8`, `rune` = `int32` (Unicode)
- Go **không tự động chuyển đổi** kiểu — phải cast tường minh
