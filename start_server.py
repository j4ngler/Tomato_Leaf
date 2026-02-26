#!/usr/bin/env python3
"""
Script khởi động server cho mobile app
Chạy server trên máy tính, điện thoại kết nối qua WiFi
"""

import socket
import subprocess
import sys
import os
from pathlib import Path

def get_local_ip():
    """Lấy IP local của máy tính"""
    try:
        # Tạo socket để kết nối (không thực sự kết nối)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def check_port(port):
    """Kiểm tra port có đang được sử dụng không"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def main():
    print("=" * 60)
    print("🌱 TOMATO LEAF DISEASE DETECTION SERVER")
    print("=" * 60)
    
    # Kiểm tra file model
    model_path = Path("best.pt")
    if not model_path.exists():
        print("⚠️  CẢNH BÁO: Không tìm thấy file model 'best.pt'")
        print("   Vui lòng đảm bảo file model ở cùng thư mục với server.py")
        print()
    
    # Lấy IP local
    local_ip = get_local_ip()
    port = 8000
    
    print(f"📡 Server sẽ chạy tại:")
    print(f"   - Local:  http://localhost:{port}")
    print(f"   - Network: http://{local_ip}:{port}")
    print()
    
    # Kiểm tra port
    if check_port(port):
        print(f"⚠️  Port {port} đang được sử dụng!")
        print("   Vui lòng đóng ứng dụng khác đang dùng port này")
        sys.exit(1)
    
    print("📱 Để kết nối từ điện thoại:")
    print(f"   1. Đảm bảo điện thoại và máy tính cùng WiFi")
    print(f"   2. Trong app mobile, cấu hình API_URL = 'http://{local_ip}:8000'")
    print()
    print("🚀 Đang khởi động server...")
    print("=" * 60)
    print()
    
    # Chạy server
    try:
        import uvicorn
        uvicorn.run(
            "server:app",
            host="0.0.0.0",  # Cho phép kết nối từ mạng local
            port=port,
            reload=False,  # Tắt reload để tránh lỗi khi chạy từ script
        )
    except KeyboardInterrupt:
        print("\n\n👋 Đã dừng server")
    except Exception as e:
        print(f"\n❌ Lỗi khi khởi động server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
