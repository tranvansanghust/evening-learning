# Bài 1 — Packages (Gói)

**Nguồn:** https://go.dev/tour/basics/1

## Lý thuyết

Mọi chương trình Go đều được tổ chức thành các **package** (gói). Chương trình bắt đầu chạy từ package tên là `main`.

Quy ước: tên package trùng với phần cuối của import path.  
Ví dụ: package `"math/rand"` → tên package là `rand`.

## Ví dụ

```go
package main

import (
    "fmt"
    "math/rand"
)

func main() {
    fmt.Println("My favorite number is", rand.Intn(10))
}
```

## Điểm cần nhớ

- Mọi file Go phải bắt đầu bằng `package <tên>`
- Package `main` là điểm vào của chương trình
- Tên package = phần cuối của import path (vd: `math/rand` → dùng `rand.Xxx`)
