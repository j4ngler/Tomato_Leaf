# Báo cáo dự án: Hệ thống nhận diện bệnh lá cà chua

## 1. Giới thiệu chung

Nông nghiệp là lĩnh vực chịu ảnh hưởng rất lớn từ sâu bệnh, đặc biệt với các cây trồng có giá trị như **cà chua**. Việc phát hiện bệnh sớm giúp giảm thiểu thất thoát năng suất và chi phí thuốc bảo vệ thực vật. Tuy nhiên, không phải người trồng nào cũng có điều kiện tiếp cận chuyên gia bệnh cây.

Dự án này xây dựng một hệ thống **nhận diện bệnh trên lá cà chua bằng trí tuệ nhân tạo**, cho phép người dùng chỉ cần **chụp một bức ảnh lá** là đã có thể nhận được **gợi ý về loại bệnh** mà lá đang mắc phải. Hệ thống tập trung vào ba bệnh phổ biến:

- Bệnh cháy lá sớm
- Bệnh đốm vi khuẩn
- Bệnh virus xoăn vàng lá

Mục tiêu là tạo ra một công cụ dễ dùng, giúp người không chuyên về công nghệ vẫn có thể tận dụng AI để hỗ trợ sản xuất.

---

## 2. Dữ liệu và chuẩn bị ban đầu

### 2.1. Thu thập và chọn lọc dữ liệu

Hệ thống được xây dựng trên cơ sở một bộ ảnh công khai về bệnh cây trồng. Từ bộ dữ liệu lớn ban đầu, dự án:

- Lọc ra các ảnh liên quan đến **lá cà chua**.
- Phân loại ảnh thành **ba nhóm bệnh** đã nêu ở trên.
- Loại bỏ các ảnh không rõ nét, sai chủ đề hoặc chất lượng quá thấp.

Kết quả là một tập ảnh tập trung, chỉ gồm các trường hợp liên quan trực tiếp tới lá cà chua, tạo nền tảng tốt cho quá trình huấn luyện mô hình.

### 2.2. Cân bằng và làm giàu dữ liệu

Trong thực tế, số lượng ảnh của mỗi bệnh không giống nhau. Một số bệnh xuất hiện ít hơn nhiều so với các bệnh khác. Nếu huấn luyện trực tiếp trên dữ liệu như vậy, mô hình rất dễ **thiên vị** những bệnh có nhiều dữ liệu.

Để khắc phục, dự án áp dụng các kỹ thuật:

- **Cân bằng số lượng ảnh giữa các bệnh** bằng cách nhân bản các ảnh của lớp ít và tạo thêm các biến thể mới từ chúng.
- **Làm giàu dữ liệu** thông qua:
  - Xoay, lật ảnh.
  - Thay đổi độ sáng, độ tương phản, màu sắc.
  - Cắt lại khung hình, làm mờ nhẹ, v.v.

Nhờ đó, mỗi bệnh có số lượng ảnh tương đương nhau, và mô hình được “nhìn thấy” nhiều kiểu hình thái lá khác nhau, giúp **tăng khả năng tổng quát** khi gặp ảnh trong thực tế.

### 2.3. Chuẩn hóa cấu trúc dữ liệu cho mô hình AI

Mô hình nhận diện được sử sử dụng thuộc họ **YOLO**, vốn yêu cầu dữ liệu được sắp xếp theo cấu trúc và nhãn đặc biệt. Dự án tổ chức dữ liệu theo hai tầng:

- **Tầng phân lớp (classification)** để dễ thao tác ban đầu:

  ```
  dataset/
  ├── Early_blight/
  ├── Bacterial_spot/
  └── Yellow_Leaf_Curl_Virus/
  ```

  Tại đây, mỗi ảnh thuộc một trong ba thư mục trên, tương ứng với ba loại bệnh mục tiêu.

- **Tầng phát hiện (object detection) theo chuẩn YOLO**, dùng cho huấn luyện mô hình:

  ```
  dataset_detection_hub/
  ├── images/
  │   ├── train/
  │   ├── val/
  │   └── test/
  ├── labels/
  │   ├── train/
  │   ├── val/
  │   └── test/
  └── data.yaml
  ```

  - Mỗi ảnh trong `images/...` có **một file nhãn `.txt` cùng tên** trong `labels/...`.
  - Mỗi dòng trong file nhãn có dạng: `class_id x_center y_center width height` (tọa độ đã chuẩn hóa về \[0,1\]).
  - Trong phiên bản hiện tại, mỗi ảnh tương ứng **1 vùng bệnh phủ toàn bộ lá**, nên **số lượng instance bằng đúng số lượng ảnh**.

Dữ liệu được **chia theo tỉ lệ 70% train – 15% val – 15% test** cho từng lớp; sau khi làm giàu lên 6000 ảnh/lớp, ta có:

- **Tổng số ảnh**: ~18.000 (mỗi lớp ~6.000 ảnh).
- **Mỗi lớp**:
  - Train: ~4.200 ảnh.
  - Val: ~900 ảnh.
  - Test: ~900 ảnh.
- **Toàn bộ tập**:
  - Train: ~12.600 ảnh / 12.600 instance.
  - Val: ~2.700 ảnh / 2.700 instance.
  - Test: ~2.700 ảnh / 2.700 instance.

Các thông tin về vị trí thư mục, số lớp, tên lớp được mô tả trong file cấu hình `data.yaml` để framework YOLO có thể tự động đọc đúng dữ liệu.

---

## 3. Huấn luyện mô hình nhận diện bệnh

### 3.1. Lựa chọn mô hình

Dự án sử dụng một phiên bản hiện đại và gọn nhẹ của YOLO, được thiết kế cho:

- Tốc độ xử lý nhanh.
- Khả năng chạy tốt trên các loại **GPU tầm trung** như NVIDIA RTX 3050.
- Tính linh hoạt để triển khai trên nhiều môi trường khác nhau (máy chủ, thiết bị biên…).

Ở giai đoạn đầu, nhóm chọn **biến thể nhỏ nhất của mô hình** để thử nghiệm. Cách làm này giúp:

- Kiểm tra toàn bộ pipeline nhanh chóng.
*- Tối ưu cấu hình trước khi chuyển sang các mô hình lớn và chính xác hơn.*

### 3.2. Quy trình huấn luyện

Trên bộ dữ liệu đã được chuẩn hóa và chia tách, mô hình được huấn luyện với quy trình và thiết lập chính như sau:

- **Chuẩn hóa ảnh đầu vào**:
  - Tất cả ảnh được resize về một độ phân giải cố định (ví dụ 640×640) trước khi đưa vào mạng.
  - Kênh màu được chuẩn hóa về không gian RGB.

- **Chia tập huấn luyện/kiểm định/kiểm tra**:
  - Train: ~70% số ảnh của từng lớp (dùng để cập nhật trọng số).
  - Validation: ~15% (dùng để theo dõi quá trình học, phát hiện overfitting).
  - Test: ~15% (chỉ dùng để đánh giá cuối cùng).

- **Làm giàu dữ liệu trong lúc train (online augmentation)**:
  - Xoay nhẹ, lật ngang/dọc.
  - Cắt lại khung hình, zoom in/out.
  - Thay đổi độ sáng, độ tương phản, màu sắc, làm mờ nhẹ.
  - Những biến đổi này được áp dụng ngẫu nhiên cho từng batch, giúp mô hình **ít bị phụ thuộc** vào một điều kiện chụp cụ thể.

- **Một số siêu tham số (hyperparameter) chính**  
  (dựa trên cấu hình mặc định của Ultralytics YOLO, điều chỉnh cho phù hợp GPU tầm trung):
  - **Batch size**: khoảng 16–32 ảnh/batch, tùy dung lượng bộ nhớ GPU.
  - **Số epoch**: 50–100 vòng lặp qua toàn bộ tập train, dừng sớm nếu validation không còn cải thiện.
  - **Kích thước ảnh (imgsz)**: 640×640.
  - **Tối ưu hóa**: SGD hoặc AdamW với:
    - Learning rate khởi điểm khoảng 0,01 (kèm lịch giảm LR theo cosine).
    - Momentum ~0,9.
    - Weight decay cỡ 5e-4 để giảm overfitting.
  - **Early stopping**: dừng huấn luyện nếu metric trên tập validation không được cải thiện sau một số epoch liên tiếp.

Nhờ lựa chọn cấu hình vừa phải và sử dụng GPU tầm trung, thời gian huấn luyện vẫn nằm trong giới hạn chấp nhận được, đồng thời mô hình đạt được mức độ chính xác đủ tốt để đưa vào triển khai thực tế.

### 3.3. Kết quả huấn luyện

Sau khi huấn luyện, mô hình được **đánh giá trên tập test (~2.700 ảnh, mỗi lớp 900 ảnh)**. Công cụ Ultralytics sinh ra một bảng kết quả tóm tắt theo từng lớp bệnh, bao gồm:

- **Precision (P)**: tỷ lệ dự đoán bệnh đúng trên tổng số dự đoán bệnh.
- **Recall (R)**: tỷ lệ phát hiện đúng trên tổng số vùng bệnh thực tế.
- **mAP@0.5**: mean Average Precision tại ngưỡng IoU 0,5.
- **mAP@0.5:0.95**: mAP trung bình trên nhiều ngưỡng IoU (từ 0,5 đến 0,95).

Bảng sau là kết quả tiêu biểu thu được (trích từ log chạy validate):

| Lớp bệnh               | Số ảnh | Số instance | Precision (P) | Recall (R) | mAP@0.5 | mAP@0.5:0.95 |
|------------------------|:------:|:-----------:|:-------------:|:----------:|:-------:|:-------------:|
| Early_blight           |  900   |    900      |     0.999     |   0.999    |  0.999  |     0.995     |
| Bacterial_spot         |  900   |    900      |     0.999     |   0.999    |  0.999  |     0.995     |
| Yellow_Leaf_Curl_Virus |  900   |    900      |     0.999     |   0.999    |  0.999  |     0.995     |

Có thể thấy mô hình đạt **độ chính xác và khả năng bao phủ rất cao** trên cả ba lớp bệnh, với mAP@0.5 xấp xỉ 0,999 và mAP@0.5:0.95 khoảng 0,995. Điều này cho thấy:

- Mô hình phân biệt tốt giữa ba loại bệnh trong bối cảnh dữ liệu đã chuẩn bị.
- Độ tin cậy của các dự đoán cao, phù hợp để triển khai trong ứng dụng thực tế, đồng thời vẫn còn dư địa tinh chỉnh thêm nếu mở rộng sang nhiều loại bệnh hoặc điều kiện chụp đa dạng hơn.

Mô hình tốt nhất (best checkpoint) thu được từ quá trình huấn luyện được lưu lại và dùng làm **mô hình chính** trong dịch vụ AI của hệ thống.

---

## 4. Xây dựng dịch vụ AI chạy trên máy chủ

Để người dùng không cần làm việc trực tiếp với mô hình học sâu, dự án xây dựng một **dịch vụ web** đóng vai trò là “bộ não AI” của hệ thống.

### 4.1. Cách thức hoạt động

Khi dịch vụ được khởi động:

- Mô hình đã huấn luyện được **nạp lên bộ nhớ** một lần.
- Hệ thống sẵn sàng nhận yêu cầu từ bên ngoài thông qua các địa chỉ (API) rõ ràng.

Các chức năng chính của dịch vụ gồm:

- **Kiểm tra trạng thái**: cho phép các ứng dụng khác biết server đang hoạt động bình thường.
- **Nhận diện bệnh**:
  - Nhận một ảnh lá cà chua do người dùng gửi lên.
  - Xử lý ảnh và đưa qua mô hình để phân tích.
  - Trả về danh sách các bệnh nghi ngờ, cùng với:
    - Tên bệnh.
    - Mức độ tin cậy.
    - Vị trí vùng bệnh trên ảnh (nếu cần thiết).

Nhờ đó, các ứng dụng bên ngoài (web, di động) chỉ cần gửi ảnh và đọc kết quả, không cần triển khai mô hình phức tạp trên thiết bị của mình.

---
