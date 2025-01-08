# ModernTensor CLI

ModernTensor là một dự án tập trung vào việc xây dựng một công cụ dòng lệnh (CLI) hỗ trợ lập trình và triển khai các mô hình Tensor trong các ứng dụng hiện đại. Hiện dự án đang trong giai đoạn phát triển ban đầu (development stage) và vẫn còn rất nhiều hạng mục cần được hoàn thiện.

## Tính năng hiện có

- **CLI tiện dụng**: Cung cấp câu lệnh gọn nhẹ, dễ dàng tương tác.
- **Khả năng mở rộng**: Hỗ trợ tích hợp thêm các thư viện và công cụ mở rộng trong tương lai.
- **Thiết kế linh hoạt**: Cho phép tuỳ chỉnh, cấu hình thông qua các tệp thiết lập (config).

## Lộ trình phát triển

1. **Phiên bản thử nghiệm (Alpha)**  
   - Hoàn thiện các thao tác cơ bản và cấu trúc CLI.  
   - Cung cấp tài liệu hướng dẫn sử dụng ban đầu.

2. **Phiên bản Beta**  
   - Tối ưu hiệu năng, hỗ trợ đa nền tảng.  
   - Thêm các thư viện và plugin bổ sung.

3. **Phiên bản chính thức**  
   - Cải thiện độ ổn định, tăng cường bảo mật.  
   - Hỗ trợ sâu hơn cho các mô hình và thuật toán máy học.

## Yêu cầu cài đặt

- **Python** (phiên bản 3.7 trở lên)
- Môi trường ảo **virtualenv** hoặc **conda** (khuyến khích)
- **Git** (để clone dự án)

## Hướng dẫn cài đặt

1. Clone source code từ kho lưu trữ:
   ```bash
   git clone https://github.com/yourusername/moderntensor-cli.git
   cd moderntensor-cli
   ```

2. Tạo môi trường ảo (tuỳ chọn nhưng được khuyến nghị):
   ```bash
    python -m venv venv
    source venv/bin/activate  # Trên Linux/Mac
    .\venv\Scripts\activate   # Trên Windows
   ```

3. Cài đặt các thư viện phụ thuộc:
   ```bash
    pip install -e .
   ```

## Cách sử dụng

Sau khi cài đặt thành công, bạn có thể sử dụng lệnh `mtcli` trên terminal:
```bash
mtcli --help
```

## Đóng góp

ModernTensor rất hoan nghênh mọi đóng góp từ cộng đồng:
* Tạo **Issues** hoặc **Pull Requests** trên kho GitHub.
* Tham gia thảo luận, đóng góp ý tưởng và đề xuất các tính năng mới.

## Liên hệ

* Email: `sonlearn155@gmail.com`
* Github: ![son](https://github.com/sonson0910)