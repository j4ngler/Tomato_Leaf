import React, { useState, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Platform,
  Modal,
  Dimensions,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import axios from 'axios';

// Cấu hình server API
const API_URL = __DEV__
  ? Platform.OS === 'android'
    ? 'http://10.0.2.2:8000' // Android emulator
    : 'http://localhost:8000' // iOS simulator
  : 'https://your-server.com'; // Production server

const CLASS_NAMES = {
  0: 'Early_blight',
  1: 'Bacterial_spot',
  2: 'Yellow_Leaf_Curl_Virus',
};

const CLASS_COLORS = {
  0: '#FF6B6B', // Đỏ - Early blight
  1: '#4ECDC4', // Xanh lá - Bacterial spot
  2: '#FFE66D', // Vàng - Yellow Leaf Curl Virus
};

const CLASS_DESCRIPTIONS = {
  0: 'Bệnh cháy lá sớm - Nấm Alternaria solani',
  1: 'Đốm vi khuẩn - Vi khuẩn Xanthomonas',
  2: 'Virus cuốn lá vàng - Begomovirus',
};

const { width, height } = Dimensions.get('window');

export default function App() {
  const [facing, setFacing] = useState('back');
  const [permission, requestPermission] = useCameraPermissions();
  const [capturedImage, setCapturedImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [showResults, setShowResults] = useState(false);
  const cameraRef = useRef(null);

  const takePicture = async () => {
    if (!cameraRef.current) return;

    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.8,
        base64: false,
      });

      if (photo) {
        setCapturedImage(photo.uri);
        // Tự động gửi ảnh lên server
        await detectDisease(photo.uri);
      }
    } catch (error) {
      Alert.alert('Lỗi', 'Không thể chụp ảnh: ' + error.message);
    }
  };

  const detectDisease = async (imageUri) => {
    if (!imageUri) return;

    setLoading(true);
    setResults(null);
    setShowResults(false);

    try {
      // Tạo FormData để gửi ảnh
      const formData = new FormData();
      const filename = imageUri.split('/').pop();
      const match = /\.(\w+)$/.exec(filename);
      const type = match ? `image/${match[1]}` : 'image/jpeg';

      formData.append('file', {
        uri: imageUri,
        name: filename || 'photo.jpg',
        type: type,
      });

      // Gửi request đến server
      const response = await axios.post(`${API_URL}/predict`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 30000, // 30 giây timeout
      });

      setResults(response.data);
      setShowResults(true);
    } catch (error) {
      console.error('Error:', error);
      if (error.response) {
        Alert.alert(
          'Lỗi Server',
          `Server trả về lỗi: ${error.response.data?.detail || error.message}`
        );
      } else if (error.request) {
        Alert.alert(
          'Lỗi Kết Nối',
          'Không thể kết nối đến server. Vui lòng kiểm tra:\n' +
          `1. Server đang chạy tại ${API_URL}\n` +
          '2. Đảm bảo điện thoại và máy tính cùng mạng WiFi\n' +
          '3. Kiểm tra firewall/antivirus'
        );
      } else {
        Alert.alert('Lỗi', 'Có lỗi xảy ra: ' + error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const resetCamera = () => {
    setCapturedImage(null);
    setResults(null);
    setShowResults(false);
  };

  if (!permission) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" />
        <Text>Đang kiểm tra quyền truy cập...</Text>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>
          Ứng dụng cần quyền truy cập camera để chụp ảnh.
        </Text>
        <TouchableOpacity style={styles.permissionButton} onPress={requestPermission}>
          <Text style={styles.permissionButtonText}>Cấp quyền</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Camera View - Fullscreen */}
      <CameraView
        ref={cameraRef}
        style={styles.camera}
        facing={facing}
      >
        {/* Overlay UI */}
        <View style={styles.overlay}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.headerTitle}>🌱 Phát Hiện Bệnh Lá Cà Chua</Text>
          </View>

          {/* Loading indicator */}
          {loading && (
            <View style={styles.loadingOverlay}>
              <ActivityIndicator size="large" color="#fff" />
              <Text style={styles.loadingText}>Đang phân tích...</Text>
            </View>
          )}

          {/* Capture button */}
          <View style={styles.bottomControls}>
            <TouchableOpacity
              style={styles.captureButton}
              onPress={takePicture}
              disabled={loading}
            >
              <View style={styles.captureButtonInner} />
            </TouchableOpacity>
          </View>
        </View>
      </CameraView>

      {/* Results Modal */}
      <Modal
        visible={showResults}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowResults(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            {/* Captured Image */}
            {capturedImage && (
              <Image source={{ uri: capturedImage }} style={styles.resultImage} />
            )}

            {/* Results */}
            <View style={styles.resultsContainer}>
              <Text style={styles.resultTitle}>
                Kết quả phát hiện ({results?.num_detections || 0} bệnh)
              </Text>

              {results?.diseases && results.diseases.length > 0 ? (
                results.diseases.map((disease, index) => (
                  <View
                    key={index}
                    style={[
                      styles.diseaseCard,
                      { borderLeftColor: CLASS_COLORS[disease.class_id] || '#666' },
                    ]}
                  >
                    <View style={styles.diseaseHeader}>
                      <View
                        style={[
                          styles.diseaseChip,
                          { backgroundColor: CLASS_COLORS[disease.class_id] || '#666' },
                        ]}
                      >
                        <Text style={styles.diseaseName}>
                          {disease.name || `Class ${disease.class_id}`}
                        </Text>
                      </View>
                      <Text style={styles.confidence}>
                        {(disease.confidence * 100).toFixed(1)}%
                      </Text>
                    </View>
                    <Text style={styles.description}>
                      {CLASS_DESCRIPTIONS[disease.class_id] || 'Không có mô tả'}
                    </Text>
                  </View>
                ))
              ) : (
                <Text style={styles.noResult}>
                  Không phát hiện bệnh nào trong ảnh này.
                </Text>
              )}
            </View>

            {/* Close button */}
            <TouchableOpacity
              style={styles.closeButton}
              onPress={resetCamera}
            >
              <Text style={styles.closeButtonText}>Chụp Ảnh Mới</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  camera: {
    flex: 1,
  },
  overlay: {
    flex: 1,
    backgroundColor: 'transparent',
    justifyContent: 'space-between',
  },
  header: {
    paddingTop: Platform.OS === 'ios' ? 50 : 20,
    paddingHorizontal: 20,
    paddingBottom: 10,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
  },
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#fff',
    marginTop: 10,
    fontSize: 16,
  },
  bottomControls: {
    paddingBottom: Platform.OS === 'ios' ? 40 : 20,
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingTop: 20,
  },
  captureButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderWidth: 4,
    borderColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  captureButtonInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#fff',
  },
  // Modal styles
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    width: width * 0.9,
    maxHeight: height * 0.8,
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 20,
  },
  resultImage: {
    width: '100%',
    height: 200,
    borderRadius: 10,
    marginBottom: 20,
    resizeMode: 'contain',
  },
  resultsContainer: {
    maxHeight: height * 0.4,
  },
  resultTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333',
  },
  diseaseCard: {
    marginBottom: 12,
    borderLeftWidth: 4,
    padding: 12,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
  },
  diseaseHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  diseaseChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  diseaseName: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
  confidence: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  description: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  noResult: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
    textAlign: 'center',
    padding: 16,
  },
  closeButton: {
    marginTop: 20,
    padding: 15,
    backgroundColor: '#4CAF50',
    borderRadius: 10,
    alignItems: 'center',
  },
  closeButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  errorText: {
    fontSize: 16,
    color: '#d32f2f',
    textAlign: 'center',
    marginBottom: 16,
  },
  permissionButton: {
    backgroundColor: '#4CAF50',
    padding: 15,
    borderRadius: 10,
    marginTop: 20,
  },
  permissionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
});
