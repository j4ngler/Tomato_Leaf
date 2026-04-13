from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _arial_path() -> str:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for name in ("arial.ttf", "Arial.ttf"):
        p = os.path.join(windir, "Fonts", name)
        if os.path.isfile(p):
            return p
    return ""


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def markdown_to_story(md_text: str, styles: dict) -> list:
    story = []
    for raw in md_text.splitlines():
        line = raw.rstrip()

        if not line.strip():
            story.append(Spacer(1, 0.18 * cm))
            continue

        if line.startswith("# "):
            story.append(Paragraph(_escape(line[2:].strip()), styles["title"]))
            continue
        if line.startswith("## "):
            story.append(Paragraph(_escape(line[3:].strip()), styles["h2"]))
            continue
        if line.startswith("### "):
            story.append(Paragraph(_escape(line[4:].strip()), styles["h3"]))
            continue

        if line.startswith("- "):
            story.append(Paragraph(f"• {_escape(line[2:].strip())}", styles["body"]))
            continue

        # Giữ nguyên dòng bảng markdown để dễ đọc trong PDF
        if line.startswith("|") and line.endswith("|"):
            story.append(Paragraph(_escape(line), styles["mono"]))
            continue

        story.append(Paragraph(_escape(line), styles["body"]))

    return story


def main() -> None:
    root = Path(__file__).resolve().parent
    in_path = root / "ket_qua_so_sanh_3_model.md"
    out_path = root / "ket_qua_so_sanh_3_model.pdf"

    if not in_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file markdown: {in_path}")

    arial = _arial_path()
    if not arial:
        raise FileNotFoundError("Không tìm thấy arial.ttf trong thư mục Fonts của Windows.")
    pdfmetrics.registerFont(TTFont("ArialVI", arial))

    styles = getSampleStyleSheet()
    custom_styles = {
        "title": ParagraphStyle(
            "title",
            parent=styles["Heading1"],
            fontName="ArialVI",
            fontSize=17,
            leading=22,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=styles["Heading2"],
            fontName="ArialVI",
            fontSize=13,
            leading=17,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=styles["Heading3"],
            fontName="ArialVI",
            fontSize=12,
            leading=15,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=styles["BodyText"],
            fontName="ArialVI",
            fontSize=10.5,
            leading=14,
            spaceAfter=3,
        ),
        "mono": ParagraphStyle(
            "mono",
            parent=styles["Code"],
            fontName="ArialVI",
            fontSize=8.5,
            leading=11,
        ),
    }

    md_text = in_path.read_text(encoding="utf-8")
    story = markdown_to_story(md_text, custom_styles)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    doc.build(story)
    print(out_path)


if __name__ == "__main__":
    main()

