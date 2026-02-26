# 📱 Cấu Hình Mobile App

## 🎯 Mục đích
- **Model chạy trên máy tính** (server Python)
- **Điện thoại chỉ hiển thị kết quả** (không cần màn hình máy tính)

## ⚙️ Cấu hình API URL

### Bước 1: Tìm IP máy tính

**Windows:**
```cmd
ipconfig
```
Tìm dòng "IPv4 Address" (ví dụ: 192.168.1.100)

**Mac/Linux:**
```bash
ifconfig
```
Hoặc:
```bash
ip addr show
```

### Bước 2: Sửa API_URL trong App.js

Mở file `Tomato_Leaf/mobile-app/App.js`, tìm dòng:

```javascript
const API_URL = __DEV__
  ? Platform.OS === 'android'
    ? 'http://10.0.2.2:8000' // Android emulator
    : 'http://localhost:8000' // iOS simulator
  : 'https://your-server.com'; // Production server
```

**Sửa thành IP máy tính của bạn:**

```javascript
const API_URL = 'http://192.168.1.100:8000'; // Thay bằng IP máy tính của bạn
```

### Bước 3: Chạy server trên máy tính

```bash
cd Tomato_Leaf
python start_server.py
```

Hoặc:

```bash
python server.py
```

Server sẽ chạy tại: `http://YOUR_IP:8000`

### Bước 4: Chạy app trên điện thoại

```bash
cd Tomato_Leaf/mobile-app
npm start
```

Quét QR code bằng Expo Go app.

## ✅ Kiểm tra kết nối

1. **Từ điện thoại, mở browser:**
   - Vào: `http://YOUR_IP:8000/health`
   - Phải thấy: `{"status":"ok"}`

2. **Nếu không kết nối được:**
   - ✅ Đảm bảo điện thoại và máy tính cùng WiFi
   - ✅ Tắt firewall tạm thời
   - ✅ Kiểm tra IP đúng
   - ✅ Server đang chạy (port 8000)

## 🔧 Troubleshooting

### "Network request failed"
- Kiểm tra server đang chạy: `http://localhost:8000/health`
- Kiểm tra IP đúng
- Đảm bảo cùng WiFi

### "Connection refused"
- Firewall chặn port 8000
- Tắt firewall hoặc mở port 8000

### "Timeout"
- Server xử lý chậm
- Kiểm tra model file có tồn tại không

## 📝 Lưu ý

- **Không cần màn hình máy tính** - chỉ cần server chạy
- **Điện thoại tự động hiển thị kết quả** sau khi chụp ảnh
- **Model chạy trên máy tính** - điện thoại chỉ gửi/nhận dữ liệu
