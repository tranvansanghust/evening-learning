# Bài 6 — Named Return Values (Giá trị trả về có tên)

**Nguồn:** https://go.dev/tour/basics/6

## Lý thuyết

Go cho phép **đặt tên cho giá trị trả về**. Khi đặt tên, chúng hoạt động như biến cục bộ được khai báo sẵn trong hàm. Dùng `return` không có tham số (**naked return**) sẽ tự động trả về các biến đã đặt tên.

Chỉ dùng naked return cho hàm ngắn — trong hàm dài sẽ khó đọc.

## Ví dụ

```go
package main

import "fmt"

func split(sum int) (x, y int) {
    x = sum * 4 / 9
    y = sum - x
    return // naked return — trả về x và y
}

func main() {
    fmt.Println(split(17)) // 7 10
}
```

## Điểm cần nhớ

- Đặt tên return: `func f() (x, y int)` — x và y là biến cục bộ tự động
- **Naked return** (`return` không có giá trị) trả về các named values hiện tại
- Chỉ dùng naked return trong **hàm ngắn** (dưới ~10 dòng), hàm dài dễ gây nhầm lẫn
