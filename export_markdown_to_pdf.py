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
    raise FileNotFoundError("Không tìm thấy arial.ttf trong Windows Fonts.")


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def markdown_to_story(md_text: str, normal: ParagraphStyle, h1: ParagraphStyle, h2: ParagraphStyle, mono: ParagraphStyle):
    story = []
    for raw_line in md_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            story.append(Spacer(1, 0.18 * cm))
            continue

        if line.startswith("# "):
            story.append(Paragraph(_escape_html(line[2:]), h1))
            continue
        if line.startswith("## "):
            story.append(Paragraph(_escape_html(line[3:]), h2))
            continue
        if line.startswith("|"):
            story.append(Paragraph(_escape_html(line), mono))
            continue
        if line.startswith("- "):
            story.append(Paragraph(f"• {_escape_html(line[2:])}", normal))
            continue
        if line[:2].isdigit() and line[1] == ".":
            story.append(Paragraph(_escape_html(line), normal))
            continue

        story.append(Paragraph(_escape_html(line), normal))
    return story


def main() -> None:
    root = Path(__file__).resolve().parent
    md_path = root / "ket_qua_so_sanh_3_model.md"
    pdf_path = root / "ket_qua_so_sanh_3_model.pdf"

    md_text = md_path.read_text(encoding="utf-8")

    pdfmetrics.registerFont(TTFont("ArialVI", _arial_path()))
    styles = getSampleStyleSheet()

    normal = ParagraphStyle(
        "normal_vi",
        parent=styles["Normal"],
        fontName="ArialVI",
        fontSize=10.5,
        leading=14,
        spaceAfter=4,
    )
    h1 = ParagraphStyle(
        "h1_vi",
        parent=styles["Heading1"],
        fontName="ArialVI",
        fontSize=17,
        leading=22,
        spaceAfter=8,
    )
    h2 = ParagraphStyle(
        "h2_vi",
        parent=styles["Heading2"],
        fontName="ArialVI",
        fontSize=13,
        leading=17,
        spaceBefore=8,
        spaceAfter=6,
    )
    mono = ParagraphStyle(
        "mono_vi",
        parent=normal,
        fontName="Courier",
        fontSize=8.2,
        leading=10.5,
    )

    story = markdown_to_story(md_text, normal, h1, h2, mono)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )
    doc.build(story)
    print(str(pdf_path))


if __name__ == "__main__":
    main()

