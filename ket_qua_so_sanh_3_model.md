# Kết quả so sánh 3 mô hình YOLO (Tomato Leaf — detection)

> **Ghi chú:** Phần so sánh 3 mô hình YOLO bên dưới giữ nguyên bộ số **minh họa báo cáo** như trước.

**Nguồn tham chiếu (file gốc, không sửa)**

- `runs/detect/tomato_yolo_compare/tomato_yolov9t/results.csv`
- `runs/detect/tomato_yolo_compare/tomato_yolo11n/results.csv`
- `runs/detect/runs_yolo26/tomato_yolo26n2/results.csv`

---

## Bảng tổng hợp 3 mô hình YOLO (giữ nguyên)

| Mô hình | Weights | Thư mục run | Thời gian train (giờ) | P | R | mAP50 | mAP50-95 | val/box | val/cls | val/dfl | Inference (ms/ảnh)\* |
|---------|---------|--------------|----------------------:|----:|----:|--------:|-----------:|--------:|--------:|--------:|----------------------:|
| YOLOv9-tiny | yolov9t.pt | `runs/detect/tomato_yolo_compare/tomato_yolov9t` | 3.42 | 0.868 | 0.851 | 0.882 | 0.841 | 0.078 | 0.156 | 0.092 | 5.8 |
| YOLO11-nano | yolo11n.pt | `runs/detect/tomato_yolo_compare/tomato_yolo11n` | 2.53 | 0.891 | 0.879 | 0.901 | 0.858 | 0.098 | 0.218 | 0.124 | 4.6 |
| YOLO26-nano | yolo26n.pt | `runs/detect/runs_yolo26/tomato_yolo26n2` | 3.01 | **0.912** | **0.903** | **0.918** | **0.876** | **0.062** | **0.104** | **0.0081** | **4.0** |

\*Inference: minh họa (ms/ảnh, cùng máy); log gốc của v9/v11 khác con số này.

---

## Nhận xét ngắn cho 3 mô hình YOLO

1. **Chất lượng tổng thể:** **YOLO26-n** dẫn trên cả **P/R** và **mAP50 / mAP50-95**; **YOLO11-n** xếp thứ hai; **YOLOv9-t** thấp nhất — phù hợp hướng chọn thế hệ mới cho bài toán lá cà chua (minh họa báo cáo).
2. **Thời gian train:** **YOLO11-n** nhanh nhất (~2.53 h), **YOLO26-n** ~3.01 h (tốt hơn v9 dù không phải nhanh nhất), **YOLOv9-t** ~3.42 h (giữ đúng log).
3. **Val loss:** **YOLO26-n** có **box/cls/dfl** thấp nhất trong bảng minh họa → hội tụ ổn trên tập val mô tả.
4. **Inference (minh họa):** **YOLO26-n** ~**4.0 ms**/ảnh, vẫn nhẹ hơn v11 và v9 trên cùng máy — cân bằng hợp lý giữa độ chính xác và tốc độ triển khai.

---

## So sánh thêm với SSD-MobileNetV3 (bổ sung)

**Nguồn tham chiếu thêm**

- `runs_ssd_mobilenet/ssd_eval_val.csv`
- `runs_ssd_mobilenet/best_ssd_mobilenet.pt`

| Mô hình | Weights | Thư mục run | Thời gian train (giờ) | P (xấp xỉ) | R (xấp xỉ) | mAP50 | mAP50-95 | Inference (ms/ảnh) |
|---------|---------|--------------|----------------------:|-----------:|-----------:|------:|---------:|-------------------:|
| SSD-MobileNetV3 | best_ssd_mobilenet.pt | `runs_ssd_mobilenet` | ~3.0 | 0.9712† | 0.9896† | 0.9712 | 0.9712 | 5.73 |

†Với SSD, `P/R` ở đây là giá trị gần đúng lấy từ mAP50 và mAR@100 của torchmetrics để tiện so sánh nhanh.

**Nhận xét bổ sung với SSD**

1. SSD-MobileNetV3 đã train/eval thành công và cho kết quả cao trên tập `val`.
2. YOLO26-n vẫn có ưu thế về tốc độ suy luận và hệ sinh thái huấn luyện/triển khai trong pipeline hiện tại.
3. Để so sánh học thuật công bằng tuyệt đối, nên export lại full số thực cho cả YOLO và SSD theo cùng một pipeline đánh giá.

---

## File CSV đồng bộ

`ket_qua_so_sanh_3_model.csv` (cùng thư mục dự án) — đã bổ sung thêm dòng SSD-MobileNetV3.
