# 🌱 Tomato Leaf Disease Detector - Mobile App

Ứng dụng di động để phát hiện bệnh lá cà chua sử dụng React Native và Expo.

## 📋 Tính năng

- 📸 Chụp ảnh trực tiếp từ camera
- 🖼️ Chọn ảnh từ thư viện
- 🤖 Phân tích bệnh bằng AI (YOLO model)
- 📊 Hiển thị kết quả với độ tin cậy
- 🎨 Giao diện đẹp, dễ sử dụng

## 🚀 Cài đặt

### Yêu cầu

- Node.js (v16 trở lên)
- npm hoặc yarn
- Expo CLI: `npm install -g expo-cli`
- Android Studio (cho Android) hoặc Xcode (cho iOS)

### Bước 1: Cài đặt dependencies

```bash
cd mobile-app
npm install
```

### Bước 2: Cấu hình API URL

Mở file `App.js` và sửa `API_URL`:

```javascript
const API_URL = 'http://YOUR_SERVER_IP:8000';
```

**Lưu ý:**
- Nếu test trên emulator/simulator:
  - Android: dùng `http://10.0.2.2:8000`
  - iOS: dùng `http://localhost:8000`
- Nếu test trên thiết bị thật:
  - Đảm bảo điện thoại và máy tính cùng mạng WiFi
  - Dùng IP local của máy tính (ví dụ: `http://192.168.1.100:8000`)

### Bước 3: Chạy server API

Trong thư mục `Tomato_Leaf`:

```bash
python server.py
```

### Bước 4: Chạy app

```bash
npm start
```

Sau đó:
- Nhấn `a` để mở trên Android emulator
- Nhấn `i` để mở trên iOS simulator
- Quét QR code bằng Expo Go app trên điện thoại thật

## 📱 Build APK/IPA

### Android APK

```bash
expo build:android
```

Hoặc build local:

```bash
eas build --platform android --profile preview
```

### iOS IPA

```bash
expo build:ios
```

Hoặc:

```bash
eas build --platform ios --profile preview
```

## 🔧 Cấu trúc Project

```
mobile-app/
├── App.js              # Component chính
├── package.json        # Dependencies
├── app.json           # Expo config
└── assets/            # Icons, images
```

## 🐛 Troubleshooting

### Lỗi kết nối server

1. Kiểm tra server đang chạy: `http://YOUR_IP:8000/health`
2. Đảm bảo firewall cho phép port 8000
3. Kiểm tra IP address đúng

### Lỗi camera

1. Kiểm tra quyền camera trong Settings
2. Android: Thêm permissions trong `app.json`

### Lỗi build

1. Xóa `node_modules` và `package-lock.json`
2. Chạy lại `npm install`
3. Xóa cache: `expo start -c`

## 📝 Notes

- App sử dụng API từ server Python (FastAPI)
- Model YOLO chạy trên server, không phải trên mobile
- Có thể optimize bằng cách convert model sang TensorFlow Lite để chạy on-device

## 🔄 Cập nhật

Để cập nhật dependencies:

```bash
npm update
```

## 📄 License

MIT
