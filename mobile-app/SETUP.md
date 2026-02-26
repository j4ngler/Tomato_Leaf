# 🚀 Hướng Dẫn Setup Nhanh

## Bước 1: Cài đặt Expo CLI

```bash
npm install -g expo-cli
```

## Bước 2: Cài đặt dependencies

```bash
cd mobile-app
npm install
```

## Bước 3: Cấu hình API URL

Mở `App.js`, tìm dòng:

```javascript
const API_URL = __DEV__
  ? Platform.OS === 'android'
    ? 'http://10.0.2.2:8000'
    : 'http://localhost:8000'
  : 'https://your-server.com';
```

**Cho thiết bị thật:**
- Tìm IP máy tính: `ipconfig` (Windows) hoặc `ifconfig` (Mac/Linux)
- Sửa thành: `http://YOUR_IP:8000`

Ví dụ: `http://192.168.1.100:8000`

## Bước 4: Chạy server

Trong thư mục `Tomato_Leaf`:

```bash
python server.py
```

Kiểm tra server hoạt động: Mở browser `http://localhost:8000/health`

## Bước 5: Chạy app

```bash
npm start
```

**Chọn một trong các cách:**

### Cách 1: Expo Go (Dễ nhất - cho test nhanh)
1. Cài Expo Go trên điện thoại (App Store / Play Store)
2. Quét QR code từ terminal
3. App sẽ mở trên điện thoại

### Cách 2: Android Emulator
1. Mở Android Studio
2. Tạo/khởi động emulator
3. Trong terminal, nhấn `a`

### Cách 3: iOS Simulator (chỉ Mac)
1. Cài Xcode
2. Trong terminal, nhấn `i`

## ⚠️ Lưu ý quan trọng

1. **Thiết bị thật và máy tính phải cùng WiFi**
2. **Tắt firewall tạm thời** nếu không kết nối được
3. **Kiểm tra IP đúng** bằng cách ping từ điện thoại

## 🐛 Xử lý lỗi

### "Network request failed"
- Kiểm tra server đang chạy
- Kiểm tra IP address đúng
- Thử tắt firewall

### "Camera permission denied"
- Vào Settings > Apps > Tomato Leaf Detector > Permissions
- Bật Camera permission

### "Module not found"
```bash
rm -rf node_modules
npm install
```

## 📱 Test nhanh

1. Mở app
2. Nhấn "Chụp Ảnh" hoặc "Chọn Ảnh"
3. Chọn/chụp ảnh lá cà chua
4. Nhấn "Phân Tích Bệnh"
5. Xem kết quả!
