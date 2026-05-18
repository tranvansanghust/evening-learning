# Bài 10 — Zero Values (Giá trị không)

**Nguồn:** https://go.dev/tour/basics/10

## Lý thuyết

Trong Go, biến được khai báo mà **không có giá trị khởi tạo** sẽ tự động nhận **zero value** — giá trị mặc định tuỳ theo kiểu. Đây là đảm bảo quan trọng: Go không bao giờ để biến ở trạng thái "rác" như C.

| Kiểu | Zero value |
|---|---|
| Số (`int`, `float64`, ...) | `0` |
| Boolean | `false` |
| String | `""` (chuỗi rỗng) |
| Pointer, slice, map, channel, func | `nil` |

## Ví dụ

```go
package main

import "fmt"

func main() {
    var i int
    var f float64
    var b bool
    var s string

    fmt.Printf("%v %v %v %q\n", i, f, b, s)
    // 0 0 false ""
}
```

## Điểm cần nhớ

- Mọi biến Go đều được khởi tạo về zero value — không có "uninitialized variable"
- Số = `0`, bool = `false`, string = `""`, pointer/slice/map = `nil`
- Điều này giúp code an toàn hơn, tránh lỗi đọc bộ nhớ rác như C/C++
