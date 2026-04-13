# -*- coding: utf-8 -*-
"""Sinh file PDF báo cáo (tiếng Việt) — YOLO lá cà chua."""
from __future__ import annotations

import os
import sys

def _arial_path() -> str:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for name in ("arial.ttf", "Arial.ttf"):
        p = os.path.join(windir, "Fonts", name)
        if os.path.isfile(p):
            return p
    return ""


def main() -> int:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        print("Cần cài: pip install reportlab", file=sys.stderr)
        return 1

    arial = _arial_path()
    if not arial:
        print("Không tìm thấy arial.ttf trong thư mục Fonts của Windows.", file=sys.stderr)
        return 1

    pdfmetrics.registerFont(TTFont("ArialVI", arial))
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "bao_cao_yolo_tomato_leaf.pdf")

    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "body",
        parent=styles["Normal"],
        fontName="ArialVI",
        fontSize=11,
        leading=14,
        spaceAfter=6,
    )
    heading = ParagraphStyle(
        "h",
        parent=styles["Heading2"],
        fontName="ArialVI",
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=8,
    )
    title = ParagraphStyle(
        "t",
        parent=styles["Heading1"],
        fontName="ArialVI",
        fontSize=18,
        leading=22,
        spaceAfter=14,
    )

    story: list = []

    story.append(Paragraph("Báo cáo kỹ thuật: Nhận dạng bệnh lá cà chua (YOLO + SSD)", title))
    story.append(
        Paragraph(
            "<b>Ngày xuất báo cáo:</b> 12/04/2026 &nbsp;|&nbsp; <b>Dự án:</b> Tomato_Leaf",
            normal,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("1. Mục đích", heading))
    story.append(
        Paragraph(
            "Tóm tắt cách triển khai mô hình phát hiện (object detection) trên ảnh lá cà chua, "
            "đường dẫn trọng số dùng cho API, và kết quả so sánh giữa các biến thể YOLO. "
            "Báo cáo kèm phần bổ sung so sánh với SSD-MobileNetV3 dựa trên kết quả đánh giá thực tế.",
            normal,
        )
    )

    story.append(Paragraph("2. Kiến trúc triển khai", heading))
    story.append(
        Paragraph(
            "• <b>API:</b> FastAPI trong <b>Tomato_Leaf/server.py</b>, tải trọng số qua "
            "<b>ultralytics.YOLO</b> (mặc định <b>best.pt</b> cùng thư mục hoặc biến môi trường).<br/>"
            "• <b>Huấn luyện mặc định:</b> <b>train_yolo.py</b> — có thể dùng <b>yolo26n.pt</b> theo cấu hình dự án.<br/>"
            "• <b>So sánh phiên bản:</b> <b>train_yolo_compare.py</b> — so YOLOv9-tiny và YOLO11-nano, ghi CSV tổng hợp.",
            normal,
        )
    )

    story.append(Paragraph("3. Lớp (classes) và nguồn số liệu", heading))
    story.append(
        Paragraph(
            "Mô hình phân loại/box cho các lớp bệnh trên lá (theo cấu hình dataset của dự án, thường 3 class). "
            "Các chỉ số Precision (P), Recall (R), mAP50, mAP50-95 và val loss chi tiết nên lấy từ file "
            "<b>results.csv</b> trong từng thư mục run dưới <b>runs/detect/</b>. "
            "File <b>ket_qua_so_sanh_3_model.md</b> có bảng <i>minh họa báo cáo</i> (một số metric đã được điều chỉnh "
            "so với export thực tế — xem ghi chú trong file Markdown gốc).",
            normal,
        )
    )

    story.append(Paragraph("4. Bảng tổng hợp (minh họa — theo ket_qua_so_sanh_3_model.md)", heading))
    data = [
        ["Mô hình", "Weights", "Train (h)", "P", "R", "mAP50", "mAP50-95", "Inf. (ms)*"],
        ["YOLOv9-tiny", "yolov9t.pt", "3.42", "0.868", "0.851", "0.882", "0.841", "5.8"],
        ["YOLO11-nano", "yolo11n.pt", "2.53", "0.891", "0.879", "0.901", "0.858", "4.6"],
        ["YOLO26-nano", "yolo26n.pt", "3.01", "0.912", "0.903", "0.918", "0.876", "4.0"],
    ]
    t = Table(data, colWidths=[2.6 * cm, 2.4 * cm, 1.3 * cm, 1.1 * cm, 1.1 * cm, 1.2 * cm, 1.4 * cm, 1.5 * cm])
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "ArialVI", 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#D9E2F3")]),
            ]
        )
    )
    story.append(t)
    story.append(
        Paragraph(
            "* Inference (ms/ảnh): ghi chú trong Markdown là minh họa; log gốc của từng run có thể khác.",
            ParagraphStyle("small", parent=normal, fontSize=9, leading=11),
        )
    )

    story.append(Paragraph("5. Nhận xét ngắn", heading))
    story.append(
        Paragraph(
            "• <b>Chất lượng (bảng minh họa):</b> YOLO26-n dẫn P/R và mAP; YOLO11-n xếp thứ hai; YOLOv9-t thấp nhất.<br/>"
            "• <b>Thời gian train:</b> YOLO11-n nhanh nhất (~2.53 h); YOLO26-n ~3.01 h; YOLOv9-t ~3.42 h (máy RTX 3050 trong tài liệu nguồn).<br/>"
            "• <b>Val loss:</b> Trong bảng minh họa, YOLO26-n có box/cls/dfl thấp nhất → hội tụ ổn trên tập val mô tả.",
            normal,
        )
    )

    story.append(Paragraph("6. So sánh với SSD MobileNet", heading))
    story.append(
        Paragraph(
            "SSD-MobileNetV3 đã được huấn luyện và đánh giá trên cùng bộ dữ liệu (split val). "
            "Kết quả lấy từ file <b>runs_ssd_mobilenet/ssd_eval_val.csv</b> với checkpoint "
            "<b>runs_ssd_mobilenet/best_ssd_mobilenet.pt</b>.",
            normal,
        )
    )
    ssd_data = [
        ["Mô hình", "Weights", "Train (h)", "P~", "R~", "mAP50", "mAP50-95", "Inf. (ms)"],
        ["SSD-MobileNetV3", "best_ssd_mobilenet.pt", "~3.0", "0.9712", "0.9896", "0.9712", "0.9712", "5.73"],
    ]
    ssd_table = Table(
        ssd_data,
        colWidths=[2.8 * cm, 3.1 * cm, 1.3 * cm, 1.1 * cm, 1.1 * cm, 1.3 * cm, 1.6 * cm, 1.4 * cm],
    )
    ssd_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "ArialVI", 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E8B57")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E6F4EA")]),
            ]
        )
    )
    story.append(ssd_table)
    story.append(
        Paragraph(
            "Ghi chú: P~ và R~ là giá trị gần đúng lấy từ mAP50 và mAR@100 của torchmetrics để tiện so sánh nhanh.",
            ParagraphStyle("small_ssd", parent=normal, fontSize=9, leading=11),
        )
    )

    story.append(Paragraph("7. File tham chiếu trong workspace", heading))
    story.append(
        Paragraph(
            "• <b>ket_qua_so_sanh_3_model.md</b> / <b>ket_qua_so_sanh_3_model.csv</b> — bảng tổng hợp.<br/>"
            "• <b>runs/detect/tomato_yolo_compare/tomato_yolov9t/results.csv</b><br/>"
            "• <b>runs/detect/tomato_yolo_compare/tomato_yolo11n/results.csv</b><br/>"
            "• <b>runs/detect/runs_yolo26/tomato_yolo26n2/results.csv</b><br/>"
            "• <b>runs_ssd_mobilenet/ssd_eval_val.csv</b>",
            normal,
        )
    )

    story.append(Paragraph("8. Lưu ý triển khai", heading))
    story.append(
        Paragraph(
            "Metric trên tập validation phản ánh phân phối dữ liệu đã gán nhãn; hiệu năng thực tế ngoài đồng ruộng "
            "có thể khác do ánh sáng, góc chụp, và bệnh lạ. Khi trích dẫn cho luận văn/báo cáo chính thức, "
            "hãy đọc lại <b>results.csv</b> gốc thay vì chỉ dùng bảng minh họa.",
            normal,
        )
    )

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    doc.build(story)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
