# Báo cáo chuyển đổi ModernTensor từ Cardano sang Aptos

## Các công việc đã hoàn thành

### Smart Contracts
- [x] Chuyển đổi hợp đồng Plutus thành hợp đồng Move cho Aptos
- [x] Triển khai hợp đồng ModernTensor lên Aptos testnet
- [x] Khởi tạo các registry và tạo subnet
- [x] Đăng ký các validator và miner

### SDK Core
- [x] Tạo module `sdk/aptos_core/` để thay thế các chức năng của Cardano
- [x] Tạo client tương tác với hợp đồng (`contract_client.py`)
- [x] Tạo context cho Aptos để dễ dàng thiết lập môi trường (`context.py`)
- [x] Tạo các tiện ích cho việc quản lý địa chỉ (`address.py`)
- [x] Tạo dịch vụ tài khoản thay thế UTxO (`account_service.py`)
- [x] Tạo tiện ích tương tác với validator (`validator_helper.py`)

### Consensus Module
- [x] Cập nhật `state.py` để sử dụng Aptos thay vì Cardano
- [x] Cập nhật `node.py` cho việc tương tác với Aptos
- [x] Tạo hàm `run_validator_node()` để khởi tạo và chạy node validator với Aptos
- [x] Cập nhật `load_metagraph_data()` để tải dữ liệu từ Aptos
- [x] Thay thế cơ chế slot của Cardano bằng timestamps trong Aptos
- [x] Loại bỏ phụ thuộc vào pycardano và BlockFrostChainContext

### Documentation
- [x] Tạo README bằng tiếng Anh và tiếng Việt cho việc sử dụng Aptos
- [x] Tạo file requirements.txt cho việc cài đặt các thư viện cần thiết
- [x] Cập nhật pyproject.toml để thay thế các phụ thuộc Cardano bằng Aptos

## Các công việc còn cần thực hiện

### Core Migration
- [ ] Hoàn thiện việc chuyển đổi ValidatorNode.run() để hoạt động với Aptos
- [ ] Cập nhật các chức năng còn lại trong `node.py`

### Testing
- [ ] Tạo các test đơn vị cho module aptos_core mới
- [ ] Kiểm thử end-to-end việc chạy validator node
- [ ] Kiểm thử việc đồng thuận giữa nhiều validator

### Network
- [ ] Cập nhật các API endpoint để phản ánh mô hình Aptos
- [ ] Kiểm thử kết nối giữa miner và validator thông qua API

### Performance
- [ ] Tối ưu hóa các tương tác blockchain để giảm thiểu chi phí gas
- [ ] Phân tích hiệu suất và so sánh với phiên bản Cardano

## Lưu ý kỹ thuật

### Thay đổi mô hình từ UTxO sang Account-based
Một trong những thay đổi lớn nhất là việc chuyển từ mô hình UTxO của Cardano sang mô hình dựa trên tài khoản của Aptos. Điều này ảnh hưởng đến:

1. Cách lưu trữ và truy cập trạng thái (state storage)
2. Cơ chế đồng thuận và xác thực
3. Cách xử lý giao dịch và chi phí gas

### Chuyển đổi từ Plutus sang Move
Ngôn ngữ Move khác biệt đáng kể so với Plutus:

1. Move có mô hình bảo mật dựa trên tài nguyên (resources) thay vì UTxO
2. Move có hệ thống kiểu dữ liệu và quản lý storage khác biệt
3. Move được thiết kế để xử lý trạng thái một cách hiệu quả hơn

## Tổng kết

Việc chuyển đổi ModernTensor từ Cardano sang Aptos đã đạt được những tiến bộ đáng kể. Phần lớn cơ sở hạ tầng cốt lõi đã được chuyển đổi, bao gồm Smart contract và SDK core. Tuy nhiên, vẫn còn một số công việc cần hoàn thành để đảm bảo hệ thống hoạt động trơn tru và hiệu quả.

Với các module mới như aptos_core, chúng ta đã tạo một trừu tượng hóa tốt giúp cho việc tương tác với blockchain Aptos trở nên đơn giản hơn, tương tự với cách mà chúng ta đã làm với Cardano trước đây. Điều này sẽ giúp cho việc bảo trì và phát triển trong tương lai dễ dàng hơn. 