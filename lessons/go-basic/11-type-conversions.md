# Bài 11 — Type Conversions (Chuyển đổi kiểu)

**Nguồn:** https://go.dev/tour/basics/11

## Lý thuyết

Go **không tự động chuyển đổi kiểu** (không có implicit conversion). Phải dùng **explicit conversion** bằng cú pháp `T(v)` — chuyển giá trị `v` sang kiểu `T`.

Khác Java/Python — trong Go, kể cả `int` và `float64` cũng không tự chuyển cho nhau.

## Ví dụ

```go
package main

import (
    "fmt"
    "math"
)

func main() {
    var x, y int = 3, 4
    var f float64 = math.Sqrt(float64(x*x + y*y))  // phải cast sang float64
    var z uint = uint(f)

    fmt.Println(x, y, z) // 3 4 5
}
```

Lỗi nếu không cast:

```go
var i int = 42
var f float64 = i  // Lỗi biên dịch: cannot use i (int) as float64
```

## Điểm cần nhớ

- Cú pháp: `KiểuMới(giáTrị)` — vd: `float64(x)`, `int(f)`, `string(b)`
- Go **không implicit convert** — luôn phải cast tường minh
- Chuyển `float64` → `int` sẽ **cắt phần thập phân** (truncate, không làm tròn)
