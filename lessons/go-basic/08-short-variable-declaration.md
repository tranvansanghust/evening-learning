# Bài 8 — Short Variable Declaration (Khai báo biến ngắn)

**Nguồn:** https://go.dev/tour/basics/8

## Lý thuyết

Bên trong hàm, có thể dùng cú pháp `:=` thay cho `var` — ngắn gọn hơn, Go tự suy luận kiểu. **Ngoài hàm không dùng được `:=`** (phải dùng `var`).

`:=` là cú pháp phổ biến nhất khi viết Go thực tế.

## Ví dụ

```go
package main

import "fmt"

func main() {
    var i, j int = 1, 2
    k := 3                     // short declaration, k là int
    c, python, java := true, false, "no!"

    fmt.Println(i, j, k, c, python, java)
    // 1 2 3 true false no!
}
```

## Điểm cần nhớ

- `:=` chỉ dùng **trong hàm**, không dùng được ở cấp package
- Go tự suy luận kiểu từ giá trị bên phải
- `:=` kết hợp khai báo + gán trong 1 bước — tiện hơn `var`
- Nếu biến đã tồn tại, `:=` trong cùng scope là lỗi biên dịch (dùng `=` thay thế)
