# Bài 12 — Type Inference (Suy luận kiểu)

**Nguồn:** https://go.dev/tour/basics/12

## Lý thuyết

Khi khai báo biến **có giá trị khởi tạo** mà không chỉ định kiểu, Go tự **suy luận kiểu** từ giá trị bên phải. Áp dụng cho cả `var` lẫn `:=`.

Điều này giúp code ngắn gọn mà vẫn type-safe.

## Ví dụ

```go
package main

import "fmt"

func main() {
    v := 42          // int
    f := 3.14        // float64
    c := 0.867 + 0.5i // complex128
    s := "hello"     // string

    fmt.Printf("v=%v (%T)\n", v, v)
    fmt.Printf("f=%v (%T)\n", f, f)
    fmt.Printf("c=%v (%T)\n", c, c)
    fmt.Printf("s=%v (%T)\n", s, s)
}
```

Suy luận từ kiểu của biến khác:

```go
var i int = 10
j := i       // j là int (suy từ i)
k := 3.14    // k là float64 (suy từ hằng số thực)
```

## Điểm cần nhớ

- Số nguyên → `int`, số thực → `float64`, số phức → `complex128`
- Kiểu suy luận từ biến: theo kiểu của biến nguồn
- Kiểu suy luận từ hằng số không kiểu (untyped constant): tuỳ precision
