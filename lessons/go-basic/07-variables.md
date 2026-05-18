# Bài 7 — Variables (Biến)

**Nguồn:** https://go.dev/tour/basics/7

## Lý thuyết

Dùng từ khoá `var` để khai báo biến. Kiểu dữ liệu viết ở cuối. Có thể khai báo nhiều biến cùng lúc. Nếu có giá trị khởi tạo, có thể bỏ kiểu — Go sẽ tự suy luận.

`var` có thể dùng ở cấp **package** (ngoài hàm) hoặc cấp **hàm**.

## Ví dụ

```go
package main

import "fmt"

var c, python, java bool  // cấp package

func main() {
    var i int              // cấp hàm
    fmt.Println(i, c, python, java) // 0 false false false
}
```

Khai báo với giá trị khởi tạo:

```go
var i, j int = 1, 2
var x, y = true, "hello"  // bỏ kiểu, Go tự suy luận
```

## Điểm cần nhớ

- Cú pháp: `var tênBiến kiểu` hoặc `var tênBiến = giáTrị`
- Biến chưa khởi tạo = **zero value**: `0` (số), `false` (bool), `""` (string)
- `var` dùng được cả trong và ngoài hàm
