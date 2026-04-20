# Báo cáo tóm gọn: Điều khiển PTZ qua ONVIF

## Đầu vào
- Camera có hỗ trợ ONVIF cho PTZ (pan/tilt/zoom) và cung cấp thông tin cấu hình qua SOAP.
- Thông tin kết nối được truyền qua các tham số cấu hình (ví dụ IP máy camera, cổng ONVIF thường là HTTP, tên người dùng và mật khẩu).
- Với kịch bản tự động theo góc:
  - Biên pan cần quét và bước dịch chuyển theo pan.
  - Tốc độ di chuyển theo pan và tilt.
  - Tilt được giữ cố định hoặc tự động lấy theo trung điểm dải.
- Với kịch bản tự động theo vận tốc:
  - Vận tốc pan/tilt/zoom theo dạng chuẩn hoá (thường nằm trong dải [-1, 1] tuỳ camera).
  - Thời lượng “nhích” cho mỗi lần điều khiển và chu kỳ lặp.
- Với kiểm thử luồng video:
  - URL RTSP tương ứng camera và luồng phát để xác minh việc mở stream và hiển thị khung hình cơ bản.

## Quá trình thực hiện (hướng khoa học)
1. Khởi tạo kết nối ONVIF tới dịch vụ media và PTZ, sau đó chọn đúng cấu hình PTZ từ các profile mà camera công bố.
2. Truy xuất dải hoạt động của hệ pan/tilt phục vụ cho việc ra lệnh di chuyển.
   - Nếu camera cung cấp “không gian vị trí tuyệt đối”, ưu tiên trích trực tiếp min/max theo không gian này để ánh xạ thành toạ độ pan/tilt cho lệnh tuyệt đối.
   - Nếu camera không công bố “Absolute” rõ ràng, hệ thống chuyển sang đọc giới hạn pan/tilt từ các cấu trúc khác mà ONVIF trả về (ví dụ các giới hạn PanTilt).
   - Trường hợp cấu trúc dữ liệu không thuần và cần suy luận: hệ thống duyệt cấu trúc cấu hình và chỉ chấp nhận những khoảng đo được có ý nghĩa cho vị trí tuyệt đối, đồng thời loại trừ các nhánh biểu diễn vận tốc/relative (vì các nhánh này thường có dải -1..1 nhưng không tương đương “góc quay tối đa”).
3. Thiết kế hai cơ chế điều khiển tự động để phù hợp với khả năng ONVIF của từng camera:
   - Cơ chế theo “lệnh vị trí tuyệt đối”:
     - Lấy dải pan/tilt đã suy ra, khởi tạo pan ở vị trí trung điểm.
     - Theo chu kỳ đã đặt (từng giờ tại một phút cụ thể), tính vị trí pan mục tiêu bằng cách cộng/trừ một bước cố định.
     - Nếu vị trí mục tiêu vượt ngưỡng thì đảo chiều (bounce) để đảm bảo luôn nằm trong dải cho phép, từ đó tránh lỗi do ra lệnh vượt giới hạn.
     - Gửi lệnh di chuyển tuyệt đối kèm tốc độ pan/tilt và cập nhật trạng thái pan sau mỗi lần thực thi.
   - Cơ chế theo “lệnh vận tốc liên tục”:
     - Với camera chỉ cung cấp vận tốc chuẩn hoá (ContinuousPanTiltVelocitySpace), không dùng tuyệt đối theo góc.
     - Mỗi lần đến chu kỳ, gửi vận tốc pan/tilt trong một thời gian ngắn, sau đó gửi lệnh dừng để hệ thống kết thúc chuyển động rõ ràng.
     - Lặp theo mốc thời gian định trước và có cơ chế đảo chiều để quét qua lại.
4. Bổ sung chế độ thao tác trực tiếp để hiệu chuẩn và kiểm chứng phản hồi của camera:
   - Người dùng điều khiển bằng phím theo vận tốc; mỗi lần nhấn tạo chuyển động ngắn rồi dừng.
   - Khi thoát hoặc có lệnh dừng, gửi lệnh dừng để giảm rủi ro camera tiếp tục chuyển động ngoài ý muốn.
5. Xây dựng bước kiểm thử luồng RTSP bằng thư viện xử lý video để xác minh:
   - Khả năng mở stream với URL và mật khẩu tương ứng.
   - Việc thu được frame và hiển thị ở độ phân giải mong muốn (phù hợp cho kiểm tra sơ bộ trước khi tích hợp sâu).

## Kết quả đạt được
- Xác định được dải pan/tilt từ camera thông qua ONVIF và phân biệt được tình huống:
  - Camera có thể ra lệnh theo vị trí tuyệt đối (Absolute).
  - Camera chỉ hỗ trợ vận tốc/relative và phải điều khiển theo kiểu nhích theo thời gian (ContinuousMove).
- Thực hiện được lịch tự động di chuyển theo hai phương án tương ứng năng lực camera:
  - Quét theo bước pan bằng lệnh vị trí tuyệt đối với cơ chế đảo chiều khi chạm ngưỡng.
  - Quét theo nhích vận tốc liên tục với thời lượng ngắn và đảm bảo dừng hẳn sau mỗi lần.
- Có cơ chế “an toàn điều khiển” thông qua việc gửi lệnh dừng sau mỗi thao tác ngắn hoặc khi người dùng yêu cầu thoát/dừng.
- Bổ sung công cụ vận hành thực tế:
  - Trích thông tin dải PTZ để hỗ trợ chọn bước quét phù hợp với khả năng camera.
  - Kiểm thử RTSP để xác minh luồng video hoạt động ổn định trước/hoặc song song với điều khiển PTZ.

