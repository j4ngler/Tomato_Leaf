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

Mô hình nhận diện được sử sử dụng thuộc họ **YOLO**, vốn yêu cầu dữ liệu được sắp xếp theo cấu trúc nhất định. Dự án đã:

- Tự động **chia dữ liệu thành ba phần**: ảnh dùng để huấn luyện, ảnh dùng để kiểm tra trong quá trình huấn luyện, và ảnh dùng để đánh giá cuối cùng.
- Sắp xếp lại toàn bộ thư mục ảnh theo đúng cấu trúc mà mô hình cần.
- Gắn kèm các thông tin mô tả để hệ thống biết:
  - Ảnh nằm ở đâu.
  - Có bao nhiêu loại bệnh.
  - Tên từng loại bệnh là gì.

Bộ dữ liệu hoàn chỉnh này có tổng cộng khoảng **18.000 ảnh**, được cân bằng giữa ba loại bệnh và sẵn sàng để đưa vào huấn luyện.

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

Trên bộ dữ liệu đã được chuẩn hóa, mô hình được huấn luyện với các thiết lập:

- Ảnh đầu vào được **chuẩn hóa kích thước** về cùng một độ phân giải.
- Trong quá trình học, ảnh tiếp tục được **biến đổi ngẫu nhiên** (ví dụ xoay nhẹ, thay đổi ánh sáng) để mô hình học được nhiều tình huống khác nhau.
- Dữ liệu được chia thành:
  - Phần dùng để mô hình học.
  - Phần dùng để kiểm tra mô hình sau mỗi vòng lặp nhằm tránh quá khớp.

Một số tham số quan trọng như số vòng lặp huấn luyện, kích thước lô dữ liệu, kích thước ảnh… được lựa chọn sao cho **phù hợp với giới hạn bộ nhớ** nhưng vẫn tận dụng tối đa khả năng của GPU.

### 3.3. Kết quả huấn luyện

Kết quả của quá trình huấn luyện là:

- Một **mô hình đã học cách phân biệt ba bệnh** trên lá cà chua.
- Một bộ các chỉ số đánh giá (độ chính xác, khả năng nhận diện đúng loại bệnh, v.v.) dùng để so sánh và cải thiện trong các lần huấn luyện tiếp theo.

Mô hình tốt nhất thu được sẽ được lưu lại và sử dụng trong các bước triển khai tiếp theo.

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

## 5. Giao diện web cho người dùng

### 5.1. Mục tiêu

Giao diện web được thiết kế để:

- Người dùng trên máy tính hoặc trình duyệt điện thoại **có thể sử dụng ngay lập tức** mà không cần cài đặt gì thêm.
- Trình bày thông tin trực quan, thân thiện, phù hợp với người dùng không chuyên về AI.

### 5.2. Trải nghiệm sử dụng

Khi truy cập vào trang web, người dùng có thể:

1. **Chọn một bức ảnh** lá cà chua từ máy tính, hoặc **chụp ảnh mới** nếu thiết bị có camera.
2. Xem ảnh xem trước trên màn hình để đảm bảo ảnh đủ rõ nét.
3. Nhấn nút để yêu cầu hệ thống **phân tích bệnh**.
4. Nhận kết quả dưới dạng:
   - Danh sách các bệnh được phát hiện (nếu có).
   - Mức độ tin cậy tương ứng cho từng bệnh.
   - Thông điệp hướng dẫn nếu hệ thống không tìm thấy vùng bệnh rõ ràng (ví dụ đề nghị chụp gần hơn, rõ hơn).

Giao diện sử dụng phong cách hiện đại, tông màu tối, tối ưu cho cả màn hình lớn và nhỏ, giúp việc sử dụng trở nên trực quan và dễ chịu.

---

## 6. Ứng dụng di động cho người trồng

### 6.1. Vai trò của ứng dụng di động

Ứng dụng di động giúp người trồng **không cần mở máy tính** mà vẫn có thể sử dụng hệ thống. Điện thoại đóng hai vai trò:

- Là **camera** để chụp ảnh lá.
- Là **màn hình hiển thị kết quả**.

Mọi tính toán nặng nề vẫn diễn ra trên máy chủ, điện thoại chỉ gửi ảnh và nhận kết quả.

### 6.2. Quy trình sử dụng

Quy trình điển hình như sau:

1. Máy tính trong trang trại hoặc văn phòng kỹ thuật **chạy sẵn dịch vụ AI**.
2. Điện thoại cài ứng dụng và **kết nối cùng mạng WiFi** với máy tính đó.
3. Trong ứng dụng, người dùng khai báo địa chỉ máy chủ (địa chỉ IP trong mạng nội bộ).
4. Khi cần chẩn đoán:
   - Mở ứng dụng, camera sẽ bật toàn màn hình.
   - Hướng camera vào lá cà chua và chụp ảnh.
   - Ứng dụng tự động gửi ảnh lên máy chủ và chờ kết quả.
   - Kết quả hiển thị trên màn hình dưới dạng:
     - Tên bệnh.
     - Mức độ tin cậy.
     - Mô tả ngắn gọn về từng bệnh, giúp người dùng hiểu rõ hơn.

Nhờ cách thiết kế này, người dùng cuối chỉ cần **một chiếc điện thoại phổ thông**, không cần thiết bị cấu hình cao.

---

## 7. Bức tranh tổng thể: từ dữ liệu đến người dùng

Toàn bộ hệ thống có thể tóm tắt theo chuỗi bước sau:

1. **Chuẩn bị dữ liệu**  
   Thu thập, chọn lọc và làm sạch ảnh lá cà chua; cân bằng số lượng ảnh cho ba loại bệnh; làm giàu dữ liệu bằng các biến đổi.

2. **Chuẩn hóa và huấn luyện mô hình**  
   Sắp xếp lại dữ liệu theo cấu trúc chuẩn, huấn luyện mô hình nhận diện hiện đại trên GPU, đánh giá và chọn ra phiên bản mô hình tốt nhất.

3. **Đóng gói thành dịch vụ AI**  
   Đưa mô hình vào một dịch vụ web, có thể nhận ảnh từ bên ngoài, xử lý và trả về kết quả trong thời gian ngắn.

4. **Kết nối với web và ứng dụng di động**  
   Xây dựng giao diện web và app di động để người dùng có thể tương tác với hệ thống chỉ bằng vài thao tác đơn giản: chụp ảnh → gửi ảnh → xem kết quả.

Nhờ vậy, từ một mô hình AI nghiên cứu thuần túy, dự án đã phát triển thành **một giải pháp hoàn chỉnh**, sẵn sàng hỗ trợ người trồng trong việc theo dõi và phát hiện bệnh trên lá cà chua.

---

## 8. Hướng phát triển trong tương lai

Dựa trên nền tảng đã xây dựng, hệ thống có nhiều hướng mở rộng tiềm năng:

1. **Nâng cao độ chi tiết của chẩn đoán**  
   Thay vì chỉ nhận diện loại bệnh, hệ thống có thể được mở rộng để xác định chính xác vùng bệnh trên lá, giúp người dùng hiểu rõ mức độ lây lan.

2. **Bổ sung kiến thức chuyên môn**  
   Sau khi phát hiện bệnh, giao diện có thể hiển thị thêm:
   - Nguyên nhân chủ yếu.
   - Điều kiện thời tiết và canh tác dễ dẫn tới bệnh.
   - Gợi ý bước xử lý ban đầu (ở mức tham khảo, không thay thế ý kiến chuyên gia).

3. **Mở rộng sang các loại cây trồng khác**  
   Quy trình xử lý dữ liệu và huấn luyện hiện tại có thể tái sử dụng cho các cây trồng khác như ớt, khoai tây, lúa…, giúp hệ thống trở thành một “bộ công cụ chẩn đoán bệnh cây trồng” đa năng.

4. **Chạy trực tiếp trên thiết bị di động**  
   Trong tương lai, có thể nghiên cứu các phiên bản mô hình nhẹ hơn để chạy trực tiếp trên điện thoại hoặc thiết bị cầm tay, giảm phụ thuộc vào máy chủ trung tâm.

---

## 9. Kết luận

Dự án đã xây dựng thành công một hệ thống:

- **Hiểu được ba bệnh quan trọng trên lá cà chua** thông qua học sâu.
- **Đóng gói mô hình thành dịch vụ AI**, có thể tích hợp dễ dàng với các ứng dụng khác.
- **Cung cấp giao diện web và ứng dụng di động** thân thiện, giúp người trồng chỉ cần chụp ảnh là có thể nhận được gợi ý chẩn đoán bệnh.

Đây là một bước đi cụ thể trong việc đưa trí tuệ nhân tạo tới gần hơn với người làm nông, góp phần xây dựng nền nông nghiệp thông minh, hiệu quả và bền vững.