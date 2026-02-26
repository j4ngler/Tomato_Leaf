# 🚀 Hướng Dẫn Nhanh - Mobile App

## 📋 Tóm tắt
- **Model chạy trên máy tính** (server Python)
- **Điện thoại chỉ hiển thị kết quả** (không cần màn hình máy tính)
- Điện thoại = Camera + Hiển thị kết quả

## ⚡ Các bước nhanh

### 1️⃣ Chạy Server trên Máy Tính

```bash
cd Tomato_Leaf
python start_server.py
```

Server sẽ hiển thị IP của bạn, ví dụ:
```
📡 Server sẽ chạy tại:
   - Local:  http://localhost:8000
   - Network: http://192.168.1.100:8000

📱 Để kết nối từ điện thoại:
   1. Đảm bảo điện thoại và máy tính cùng WiFi
   2. Trong app mobile, cấu hình API_URL = 'http://192.168.1.100:8000'
```

**Lưu IP này lại!**

### 2️⃣ Cấu hình Mobile App

Mở `Tomato_Leaf/mobile-app/App.js`, sửa dòng 18-22:

```javascript
// Thay IP này bằng IP máy tính của bạn
const API_URL = 'http://192.168.1.100:8000';
```

### 3️⃣ Chạy Mobile App

```bash
cd Tomato_Leaf/mobile-app
npm install  # Chỉ cần chạy lần đầu
npm start
```

Quét QR code bằng Expo Go app trên điện thoại.

### 4️⃣ Sử dụng

1. Mở app trên điện thoại
2. Camera tự động bật
3. Chụp ảnh lá cà chua (nút tròn lớn)
4. **Tự động gửi lên server** → Model phân tích
5. **Kết quả hiển thị trên điện thoại** (không cần màn hình máy tính)

## ✅ Kiểm tra

Từ điện thoại, mở browser và vào:
```
http://YOUR_IP:8000/health
```

Phải thấy: `{"status":"ok"}`

## 🎯 Lưu ý

- ✅ Server chạy trên máy tính (có thể để đó, không cần màn hình)
- ✅ Điện thoại chỉ cần kết nối WiFi
- ✅ Kết quả chỉ hiển thị trên điện thoại
- ✅ Model xử lý trên máy tính, điện thoại chỉ nhận kết quả

## 🐛 Lỗi thường gặp

**"Network request failed"**
- Kiểm tra cùng WiFi
- Kiểm tra IP đúng
- Tắt firewall tạm thời

**"Connection refused"**
- Server chưa chạy
- Firewall chặn port 8000
