"""Build the bilingual executive report as a visually verified PDF."""

# ruff: noqa: E501

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/pdf/Enterprise_Process_Mining_Executive_Report_EN_TR.pdf"

NAVY = colors.HexColor("#13213C")
BLUE = colors.HexColor("#165DFF")
BLUE_LIGHT = colors.HexColor("#EAF1FF")
TEAL = colors.HexColor("#00A878")
TEAL_LIGHT = colors.HexColor("#EAF8F3")
AMBER = colors.HexColor("#F59E0B")
AMBER_LIGHT = colors.HexColor("#FFF7E6")
RED = colors.HexColor("#DC2626")
RED_LIGHT = colors.HexColor("#FFF1F1")
PURPLE = colors.HexColor("#7C3AED")
PURPLE_LIGHT = colors.HexColor("#F4EEFF")
INK = colors.HexColor("#111827")
SLATE = colors.HexColor("#475569")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#D9E2EF")
CANVAS = colors.HexColor("#F4F7FB")
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(
        TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    )


def pstyle(
    size: float = 9.2,
    leading: float | None = None,
    color=SLATE,
    bold: bool = False,
    alignment: int = TA_LEFT,
) -> ParagraphStyle:
    return ParagraphStyle(
        name=f"p-{size}-{bold}-{alignment}",
        fontName="DejaVu-Bold" if bold else "DejaVu",
        fontSize=size,
        leading=leading or size * 1.42,
        textColor=color,
        alignment=alignment,
        splitLongWords=False,
        spaceAfter=0,
        spaceBefore=0,
    )


def paragraph(
    c: canvas.Canvas,
    text: str,
    x: float,
    y_top: float,
    width: float,
    *,
    size: float = 9.2,
    leading: float | None = None,
    color=SLATE,
    bold: bool = False,
    max_height: float = 240,
) -> float:
    para = Paragraph(
        html.escape(text).replace("\n", "<br/>"),
        pstyle(size, leading, color, bold),
    )
    _, height = para.wrap(width, max_height)
    para.drawOn(c, x, y_top - height)
    return y_top - height


def page_header(
    c: canvas.Canvas,
    page: int,
    section: str,
    title: str,
    subtitle: str,
) -> float:
    c.setFillColor(CANVAS)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.roundRect(MARGIN, PAGE_H - 25 * mm, 31 * mm, 7 * mm, 3.5 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("DejaVu-Bold", 7.5)
    c.drawCentredString(MARGIN + 15.5 * mm, PAGE_H - 20.5 * mm, section.upper())
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 22)
    c.drawString(MARGIN, PAGE_H - 36 * mm, title)
    c.setFillColor(MUTED)
    c.setFont("DejaVu", 9)
    c.drawString(MARGIN, PAGE_H - 43 * mm, subtitle)
    c.setStrokeColor(LINE)
    c.line(MARGIN, PAGE_H - 48 * mm, PAGE_W - MARGIN, PAGE_H - 48 * mm)
    c.setFillColor(MUTED)
    c.setFont("DejaVu", 7)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 20.5 * mm, f"{page:02d} / 20")
    return PAGE_H - 56 * mm


def footer(c: canvas.Canvas, page: int, source: str = "reports/demo-analysis.json") -> None:
    c.setStrokeColor(LINE)
    c.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
    c.setFillColor(MUTED)
    c.setFont("DejaVu", 6.7)
    display_source = source if len(source) <= 48 else source[:45] + "..."
    c.drawString(MARGIN, 8.5 * mm, f"Source / Kaynak: {display_source}")
    c.drawCentredString(
        PAGE_W * 0.62,
        8.5 * mm,
        "Synthetic benchmark · Sentetik çalışma",
    )
    c.drawRightString(PAGE_W - MARGIN, 8.5 * mm, f"Murat Miraç Gedik · {page}")


def rounded_panel(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    fill=WHITE,
    stroke=LINE,
    radius: float = 4 * mm,
) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.7)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def metric_card(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    value: str,
    note: str,
    accent=BLUE,
) -> None:
    rounded_panel(c, x, y, w, h)
    c.setFillColor(accent)
    c.roundRect(x, y, 3 * mm, h, 1.5 * mm, fill=1, stroke=0)
    c.setFillColor(SLATE)
    c.setFont("DejaVu-Bold", 7.5)
    c.drawString(x + 6 * mm, y + h - 8 * mm, label.upper())
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 17)
    c.drawString(x + 6 * mm, y + h - 18 * mm, value)
    c.setFillColor(MUTED)
    c.setFont("DejaVu", 6.8)
    c.drawString(x + 6 * mm, y + 5 * mm, note)


def section_box(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    w: float,
    title: str,
    text: str,
    *,
    fill=WHITE,
    accent=BLUE,
    height: float = 45 * mm,
) -> None:
    rounded_panel(c, x, y_top - height, w, height, fill=fill)
    c.setFillColor(accent)
    c.circle(x + 7 * mm, y_top - 8 * mm, 2.3 * mm, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 10)
    c.drawString(x + 13 * mm, y_top - 10.5 * mm, title)
    paragraph(
        c,
        text,
        x + 6 * mm,
        y_top - 17 * mm,
        w - 12 * mm,
        size=8.2,
        leading=11.7,
        color=SLATE,
        max_height=height - 21 * mm,
    )


def bullet_list(
    c: canvas.Canvas,
    items: list[str],
    x: float,
    y_top: float,
    width: float,
    *,
    size: float = 8.7,
    gap: float = 4.2 * mm,
    color=SLATE,
) -> float:
    y = y_top
    for item in items:
        c.setFillColor(BLUE)
        c.circle(x + 1.2 * mm, y - 2.2 * mm, 1.1 * mm, fill=1, stroke=0)
        y = paragraph(
            c,
            item,
            x + 5 * mm,
            y,
            width - 5 * mm,
            size=size,
            leading=size * 1.42,
            color=color,
            max_height=50 * mm,
        )
        y -= gap
    return y


def draw_table(
    c: canvas.Canvas,
    data: list[list[object]],
    x: float,
    y_top: float,
    col_widths: list[float],
    *,
    row_heights: list[float] | None = None,
    font_size: float = 7.5,
    header_fill=NAVY,
) -> float:
    table = Table(data, colWidths=col_widths, rowHeights=row_heights)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_fill),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "DejaVu"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("LEADING", (0, 0), (-1, -1), font_size * 1.35),
                ("TEXTCOLOR", (0, 1), (-1, -1), INK),
                ("BACKGROUND", (0, 1), (-1, -1), WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    _, height = table.wrap(sum(col_widths), 200 * mm)
    table.drawOn(c, x, y_top - height)
    return y_top - height


def bar_chart(
    c: canvas.Canvas,
    labels: list[str],
    values: list[float],
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    max_value: float | None = None,
    formatter=lambda value: f"{value:.1f}",
    accent=BLUE,
) -> None:
    maximum = max_value or max(values) * 1.08
    row_h = h / len(labels)
    label_w = w * 0.38
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        baseline = y + h - (index + 1) * row_h + row_h * 0.24
        c.setFillColor(SLATE)
        c.setFont("DejaVu", 7.2)
        c.drawString(x, baseline + 2, label)
        c.setFillColor(colors.HexColor("#E7EEFD"))
        c.roundRect(x + label_w, baseline, w - label_w - 18 * mm, row_h * 0.38, 2, fill=1, stroke=0)
        fill_w = (w - label_w - 18 * mm) * min(value / maximum, 1)
        c.setFillColor(accent if index < len(labels) - 1 else TEAL)
        c.roundRect(x + label_w, baseline, fill_w, row_h * 0.38, 2, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("DejaVu-Bold", 7)
        c.drawRightString(x + w, baseline + 1.5, formatter(value))


def image_fit(
    c: canvas.Canvas,
    path: Path,
    x: float,
    y: float,
    w: float,
    h: float,
) -> None:
    from PIL import Image

    with Image.open(path) as image:
        ratio = min(w / image.width, h / image.height)
        draw_w = image.width * ratio
        draw_h = image.height * ratio
    c.drawImage(
        str(path),
        x + (w - draw_w) / 2,
        y + (h - draw_h) / 2,
        width=draw_w,
        height=draw_h,
        mask="auto",
    )


def add_page(c: canvas.Canvas) -> None:
    c.showPage()


def build() -> None:
    register_fonts()
    report = json.loads((ROOT / "reports/demo-analysis.json").read_text(encoding="utf-8"))
    bottlenecks = pd.read_csv(ROOT / "reports/tables/bottlenecks.csv")
    variants = pd.read_csv(ROOT / "reports/tables/variants.csv")
    deviations = pd.read_csv(ROOT / "reports/tables/deviations.csv")
    scenarios = pd.DataFrame(report["capacity_simulation"]["scenarios"])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUTPUT), pagesize=A4, pageCompression=1)
    c.setTitle("Enterprise Process Mining Executive Report — EN/TR")
    c.setAuthor("Murat Miraç Gedik")
    c.setSubject("Purchase-to-Pay process intelligence, SLA risk and capacity optimization")

    # 1 — Cover
    c.setFillColor(NAVY)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.rect(0, PAGE_H - 9 * mm, PAGE_W, 9 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("DejaVu-Bold", 26)
    c.drawString(MARGIN, PAGE_H - 45 * mm, "Enterprise Process Mining")
    c.drawString(MARGIN, PAGE_H - 58 * mm, "& Intelligent Workflow")
    c.drawString(MARGIN, PAGE_H - 71 * mm, "Optimization")
    c.setFillColor(colors.HexColor("#B8C6E4"))
    c.setFont("DejaVu", 13)
    c.drawString(MARGIN, PAGE_H - 86 * mm, "Purchase-to-Pay Executive Report · Yönetici Raporu")
    c.setStrokeColor(colors.HexColor("#38527D"))
    c.line(MARGIN, PAGE_H - 96 * mm, PAGE_W - MARGIN, PAGE_H - 96 * mm)
    metric_card(
        c, MARGIN, PAGE_H - 130 * mm, 38 * mm, 28 * mm, "Cases", "12,000", "deterministic", BLUE
    )
    metric_card(
        c,
        MARGIN + 42 * mm,
        PAGE_H - 130 * mm,
        42 * mm,
        28 * mm,
        "Events",
        "166,551",
        "22 activities",
        PURPLE,
    )
    metric_card(
        c,
        MARGIN + 88 * mm,
        PAGE_H - 130 * mm,
        42 * mm,
        28 * mm,
        "SLA",
        "62.08%",
        "baseline",
        AMBER,
    )
    metric_card(
        c,
        MARGIN + 134 * mm,
        PAGE_H - 130 * mm,
        46 * mm,
        28 * mm,
        "Model",
        "0.822",
        "ROC AUC",
        TEAL,
    )
    rounded_panel(
        c,
        MARGIN,
        PAGE_H - 195 * mm,
        PAGE_W - 2 * MARGIN,
        48 * mm,
        fill=colors.HexColor("#1C2E50"),
        stroke=colors.HexColor("#38527D"),
    )
    c.setFillColor(WHITE)
    c.setFont("DejaVu-Bold", 14)
    c.drawString(MARGIN + 8 * mm, PAGE_H - 160 * mm, "Decision / Karar")
    paragraph(
        c,
        "Pilot the combined optimization: low-risk approval routing, targeted Accounts Payable and treasury capacity, and supplier lead-time intervention — with human approval and payment controls retained.",
        MARGIN + 8 * mm,
        PAGE_H - 168 * mm,
        PAGE_W - 2 * MARGIN - 16 * mm,
        size=9.2,
        leading=13,
        color=colors.HexColor("#DDE7FA"),
        max_height=25 * mm,
    )
    c.setFillColor(colors.HexColor("#B8C6E4"))
    c.setFont("DejaVu", 9)
    c.drawString(MARGIN, 35 * mm, "Prepared by / Hazırlayan")
    c.setFillColor(WHITE)
    c.setFont("DejaVu-Bold", 12)
    c.drawString(MARGIN, 28 * mm, "Murat Miraç Gedik")
    c.setFillColor(colors.HexColor("#B8C6E4"))
    c.setFont("DejaVu", 8)
    c.drawString(MARGIN, 21 * mm, "Business & Data Analyst Portfolio · 28 July / Temmuz 2026")
    c.drawRightString(
        PAGE_W - MARGIN,
        15 * mm,
        "All data and value estimates are synthetic / Tüm veriler ve değerler sentetiktir",
    )
    add_page(c)

    # 2 — Executive summary EN
    y = page_header(
        c, 2, "Executive", "Executive summary", "Evidence, decision and control in one view"
    )
    card_w = (PAGE_W - 2 * MARGIN - 9 * mm) / 4
    for index, args in enumerate(
        [
            ("SLA adherence", "62.08%", "37.92% breached", AMBER),
            ("Straight-through", "42.32%", "reference path", BLUE),
            ("Rework cases", "21.98%", "repeated activity", RED),
            ("Wait share", "98.40%", "estimated", PURPLE),
        ]
    ):
        metric_card(c, MARGIN + index * (card_w + 3 * mm), y - 31 * mm, card_w, 27 * mm, *args)
    y -= 40 * mm
    section_box(
        c,
        MARGIN,
        y,
        82 * mm,
        "What the evidence says",
        "The process is not primarily constrained by touch time. Goods receipt, invoice receipt and delivery exceptions dominate elapsed time. Only 42.32% of cases follow the exact reference path, while approval and invoice exceptions create recurring control effort.",
        fill=WHITE,
        accent=BLUE,
        height=51 * mm,
    )
    section_box(
        c,
        MARGIN + 88 * mm,
        y,
        92 * mm,
        "Management decision",
        "Run a controlled combined pilot. The simulation estimates 19.42% mean-cycle reduction, +13.63 percentage-point SLA uplift, $2.21M annual value and 8.84x first-year ROI under documented synthetic assumptions.",
        fill=TEAL_LIGHT,
        accent=TEAL,
        height=51 * mm,
    )
    y -= 60 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "Scenario comparison · mean cycle hours")
    bar_chart(
        c,
        ["Baseline", "Approval automation", "AP capacity", "Combined"],
        scenarios["mean_cycle_hours"].tolist(),
        MARGIN,
        y - 53 * mm,
        PAGE_W - 2 * MARGIN,
        45 * mm,
        max_value=225,
        formatter=lambda value: f"{value:.1f} h",
    )
    y -= 62 * mm
    section_box(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        "Control statement",
        "The SLA score prioritizes analyst review. It cannot approve a purchase request, reject an invoice, authorize a payment or execute a payment. Simulation results are hypotheses for pilot design, not guaranteed savings.",
        fill=RED_LIGHT,
        accent=RED,
        height=32 * mm,
    )
    footer(c, 2)
    add_page(c)

    # 3 — Executive summary TR
    y = page_header(c, 3, "Yönetici", "Yönetici özeti", "Kanıt, karar ve kontrol tek görünümde")
    for index, args in enumerate(
        [
            ("SLA uyumu", "%62,08", "%37,92 ihlal", AMBER),
            ("Doğrudan akış", "%42,32", "referans yol", BLUE),
            ("Yeniden işleme", "%21,98", "tekrarlı aktivite", RED),
            ("Bekleme payı", "%98,40", "tahmini", PURPLE),
        ]
    ):
        metric_card(c, MARGIN + index * (card_w + 3 * mm), y - 31 * mm, card_w, 27 * mm, *args)
    y -= 40 * mm
    section_box(
        c,
        MARGIN,
        y,
        82 * mm,
        "Kanıt ne söylüyor?",
        "Süreçteki temel sorun işlem süresinden çok beklemedir. Mal kabul, fatura alımı ve teslimat istisnaları geçen süreyi belirlemektedir. Vakaların yalnızca %42,32'si referans yolu eksiksiz izlemekte; onay ve fatura istisnaları tekrarlı kontrol yükü oluşturmaktadır.",
        height=51 * mm,
    )
    section_box(
        c,
        MARGIN + 88 * mm,
        y,
        92 * mm,
        "Yönetim kararı",
        "Kontrollü birleşik pilot uygulanmalıdır. Belgelenmiş sentetik varsayımlar altında simülasyon; %19,42 ortalama çevrim süresi azalması, +13,63 puan SLA artışı, 2,21 milyon USD yıllık değer ve 8,84x ilk yıl ROI öngörmektedir.",
        fill=TEAL_LIGHT,
        accent=TEAL,
        height=51 * mm,
    )
    y -= 60 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "Senaryo karşılaştırması · ortalama çevrim saati")
    bar_chart(
        c,
        ["Mevcut durum", "Onay otomasyonu", "AP kapasitesi", "Birleşik"],
        scenarios["mean_cycle_hours"].tolist(),
        MARGIN,
        y - 53 * mm,
        PAGE_W - 2 * MARGIN,
        45 * mm,
        max_value=225,
        formatter=lambda value: f"{value:.1f} saat",
    )
    y -= 62 * mm
    section_box(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        "Kontrol beyanı",
        "SLA skoru yalnızca analist incelemesini önceliklendirir. Satın alma talebini onaylayamaz, faturayı reddedemez, ödemeyi yetkilendiremez veya gerçekleştiremez. Simülasyon bir pilot hipotezidir; garanti değildir.",
        fill=RED_LIGHT,
        accent=RED,
        height=32 * mm,
    )
    footer(c, 3)
    add_page(c)

    # 4 — Business context EN
    y = page_header(
        c,
        4,
        "Context",
        "Business question and decision scope",
        "From workflow opacity to auditable intervention",
    )
    section_box(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        "Primary question",
        "Where does Purchase-to-Pay lose time and control quality, which cases are likely to breach SLA, and which capacity or automation intervention should management pilot first?",
        fill=BLUE_LIGHT,
        accent=BLUE,
        height=31 * mm,
    )
    y -= 41 * mm
    boxes = [
        (
            "Stakeholders",
            "Procurement leadership, Accounts Payable, Treasury, Operations Excellence, Finance, Internal Control and Data teams.",
            PURPLE_LIGHT,
            PURPLE,
        ),
        (
            "Decision horizon",
            "Operational triage at Purchase Order creation and a 90-day controlled capacity pilot.",
            AMBER_LIGHT,
            AMBER,
        ),
        (
            "Success criteria",
            "Higher SLA adherence and lower cycle time without weakening approval, matching or payment controls.",
            TEAL_LIGHT,
            TEAL,
        ),
    ]
    for index, (box_title, text, fill, accent) in enumerate(boxes):
        section_box(
            c,
            MARGIN + index * 62 * mm,
            y,
            57 * mm,
            box_title,
            text,
            fill=fill,
            accent=accent,
            height=47 * mm,
        )
    y -= 58 * mm
    c.setFont("DejaVu-Bold", 11)
    c.setFillColor(INK)
    c.drawString(MARGIN, y, "Analytical question → management action")
    y -= 10 * mm
    mapping = [
        ["Question", "Evidence", "Action"],
        ["How does work flow?", "Variants + DFG", "Standardize target path"],
        ["Where does it wait?", "Bottleneck ranking", "Target capacity"],
        ["Why does it deviate?", "Conformance + rework", "Fix controls and handoffs"],
        ["Which cases need attention?", "SLA risk score", "Prioritize human review"],
        ["What should we fund?", "Queue simulation", "Pilot highest-value scenario"],
    ]
    draw_table(c, mapping, MARGIN, y, [49 * mm, 54 * mm, 77 * mm], font_size=7.8)
    footer(c, 4, "docs/architecture.md · docs/methodology.md")
    add_page(c)

    # 5 — Business context TR
    y = page_header(
        c,
        5,
        "Bağlam",
        "İş sorusu ve karar kapsamı",
        "Süreç görünmezliğinden denetlenebilir müdahaleye",
    )
    section_box(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        "Ana soru",
        "Purchase-to-Pay süreci zaman ve kontrol kalitesini nerede kaybediyor, hangi vakalar SLA ihlaline yakın ve yönetim hangi kapasite veya otomasyon müdahalesini önce pilotlamalıdır?",
        fill=BLUE_LIGHT,
        accent=BLUE,
        height=31 * mm,
    )
    y -= 41 * mm
    boxes_tr = [
        (
            "Paydaşlar",
            "Satın Alma, Accounts Payable, Hazine, Operasyonel Mükemmellik, Finans, İç Kontrol ve Veri ekipleri.",
            PURPLE_LIGHT,
            PURPLE,
        ),
        (
            "Karar ufku",
            "Purchase Order oluşumunda operasyonel önceliklendirme ve 90 günlük kontrollü kapasite pilotu.",
            AMBER_LIGHT,
            AMBER,
        ),
        (
            "Başarı ölçütü",
            "Onay, eşleştirme ve ödeme kontrollerini zayıflatmadan daha yüksek SLA ve daha düşük çevrim süresi.",
            TEAL_LIGHT,
            TEAL,
        ),
    ]
    for index, (box_title, text, fill, accent) in enumerate(boxes_tr):
        section_box(
            c,
            MARGIN + index * 62 * mm,
            y,
            57 * mm,
            box_title,
            text,
            fill=fill,
            accent=accent,
            height=47 * mm,
        )
    y -= 58 * mm
    c.setFont("DejaVu-Bold", 11)
    c.setFillColor(INK)
    c.drawString(MARGIN, y, "Analitik soru → yönetim aksiyonu")
    y -= 10 * mm
    mapping_tr = [
        ["Soru", "Kanıt", "Aksiyon"],
        ["İş nasıl akıyor?", "Varyant + DFG", "Hedef yolu standardize et"],
        ["Nerede bekliyor?", "Darboğaz sıralaması", "Kapasiteyi hedefle"],
        ["Neden sapıyor?", "Uyum + yeniden işleme", "Kontrol ve devirleri düzelt"],
        ["Hangi vaka öncelikli?", "SLA risk skoru", "İnsan incelemesini sırala"],
        ["Neye yatırım yapmalı?", "Kuyruk simülasyonu", "En değerli senaryoyu pilotla"],
    ]
    draw_table(c, mapping_tr, MARGIN, y, [49 * mm, 54 * mm, 77 * mm], font_size=7.8)
    footer(c, 5, "docs/architecture.md · docs/methodology.md")
    add_page(c)

    # 6 — Data & process EN
    y = page_header(
        c,
        6,
        "Foundation",
        "Data foundation and reference process",
        "Deterministic event evidence with a governed BPMN target",
    )
    for index, args in enumerate(
        [
            ("Events", "166,551", "validated rows", BLUE),
            ("Cases", "12,000", "reconciled IDs", PURPLE),
            ("Activities", "22", "13 target steps", AMBER),
            ("Resources", "150", "synthetic IDs", TEAL),
        ]
    ):
        metric_card(c, MARGIN + index * (card_w + 3 * mm), y - 31 * mm, card_w, 27 * mm, *args)
    y -= 40 * mm
    rounded_panel(c, MARGIN, y - 61 * mm, PAGE_W - 2 * MARGIN, 61 * mm)
    image_fit(
        c,
        ROOT / "docs/images/process-flow.png",
        MARGIN + 3 * mm,
        y - 59 * mm,
        PAGE_W - 2 * MARGIN - 6 * mm,
        57 * mm,
    )
    y -= 70 * mm
    table_data = [
        ["Quality control", "Result", "Why it matters"],
        ["Event/case reconciliation", "Passed", "Same case population and counts"],
        ["Duplicate event keys", "0", "Unique case + event index"],
        ["Null required fields", "0", "Case, activity and timestamp complete"],
        ["Time ordering", "Passed", "Monotonic events within each case"],
        ["Reproducibility", "Byte-for-byte", "Fixed seed and gzip timestamp"],
    ]
    draw_table(c, table_data, MARGIN, y, [65 * mm, 35 * mm, 80 * mm], font_size=7.7)
    footer(c, 6, "data/demo · bpmn/purchase-to-pay-reference.bpmn")
    add_page(c)

    # 7 — Data & process TR
    y = page_header(
        c,
        7,
        "Temel",
        "Veri temeli ve referans süreç",
        "Yönetişimli BPMN hedefiyle tekrarlanabilir olay kanıtı",
    )
    for index, args in enumerate(
        [
            ("Olay", "166.551", "doğrulanmış satır", BLUE),
            ("Vaka", "12.000", "mutabık kimlik", PURPLE),
            ("Aktivite", "22", "13 hedef adım", AMBER),
            ("Kaynak", "150", "sentetik kimlik", TEAL),
        ]
    ):
        metric_card(c, MARGIN + index * (card_w + 3 * mm), y - 31 * mm, card_w, 27 * mm, *args)
    y -= 40 * mm
    rounded_panel(c, MARGIN, y - 61 * mm, PAGE_W - 2 * MARGIN, 61 * mm)
    image_fit(
        c,
        ROOT / "docs/images/process-flow.png",
        MARGIN + 3 * mm,
        y - 59 * mm,
        PAGE_W - 2 * MARGIN - 6 * mm,
        57 * mm,
    )
    y -= 70 * mm
    table_data_tr = [
        ["Kalite kontrolü", "Sonuç", "Önemi"],
        ["Olay/vaka mutabakatı", "Başarılı", "Aynı vaka kümesi ve olay sayısı"],
        ["Yinelenen olay anahtarı", "0", "Vaka + olay sırası benzersiz"],
        ["Zorunlu alan boşluğu", "0", "Vaka, aktivite ve zaman eksiksiz"],
        ["Zaman sıralaması", "Başarılı", "Vaka içinde monoton olaylar"],
        ["Tekrarlanabilirlik", "Birebir aynı", "Sabit seed ve gzip zamanı"],
    ]
    draw_table(c, table_data_tr, MARGIN, y, [65 * mm, 35 * mm, 80 * mm], font_size=7.7)
    footer(c, 7, "data/demo · bpmn/purchase-to-pay-reference.bpmn")
    add_page(c)

    # 8 — Discovery & conformance EN
    y = page_header(
        c,
        8,
        "Discovery",
        "Process discovery and conformance",
        "The reference path is common, but not dominant",
    )
    metric_card(
        c, MARGIN, y - 30 * mm, 53 * mm, 27 * mm, "Variants", "14", "discovered traces", BLUE
    )
    metric_card(
        c,
        MARGIN + 58 * mm,
        y - 30 * mm,
        59 * mm,
        27 * mm,
        "Reference path",
        "42.32%",
        "5,078 cases",
        PURPLE,
    )
    metric_card(
        c,
        MARGIN + 122 * mm,
        y - 30 * mm,
        58 * mm,
        27 * mm,
        "Mean fitness",
        "91.62%",
        "edit-distance score",
        TEAL,
    )
    y -= 39 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "Largest variant populations")
    top_variants = variants.head(6)
    variant_labels = [
        "Reference",
        "Missing approval",
        "Approval rework",
        "Invoice discrepancy",
        "Late delivery",
        "3-way match failure",
    ]
    bar_chart(
        c,
        variant_labels,
        top_variants["case_count"].astype(float).tolist(),
        MARGIN,
        y - 72 * mm,
        PAGE_W - 2 * MARGIN,
        63 * mm,
        max_value=5500,
        formatter=lambda value: f"{int(value):,}",
        accent=PURPLE,
    )
    y -= 82 * mm
    dev = deviations.head(6)
    deviation_table = [["Deviation", "Cases"]] + [
        [f"{row.deviation_type}: {row.activity}", f"{int(row.case_count):,}"]
        for row in dev.itertuples()
    ]
    draw_table(c, deviation_table, MARGIN, y, [130 * mm, 50 * mm], font_size=7.7)
    footer(c, 8, "reports/tables/variants.csv · deviations.csv")
    add_page(c)

    # 9 — Discovery & conformance TR
    y = page_header(c, 9, "Keşif", "Süreç keşfi ve uyum", "Referans yol yaygın; ancak baskın değil")
    metric_card(c, MARGIN, y - 30 * mm, 53 * mm, 27 * mm, "Varyant", "14", "keşfedilen iz", BLUE)
    metric_card(
        c,
        MARGIN + 58 * mm,
        y - 30 * mm,
        59 * mm,
        27 * mm,
        "Referans yol",
        "%42,32",
        "5.078 vaka",
        PURPLE,
    )
    metric_card(
        c,
        MARGIN + 122 * mm,
        y - 30 * mm,
        58 * mm,
        27 * mm,
        "Ort. fitness",
        "%91,62",
        "edit-distance skoru",
        TEAL,
    )
    y -= 39 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "En büyük varyant grupları")
    bar_chart(
        c,
        [
            "Referans",
            "Eksik onay",
            "Onay yeniden işleme",
            "Fatura uyuşmazlığı",
            "Geç teslimat",
            "3'lü eşleşme",
        ],
        top_variants["case_count"].astype(float).tolist(),
        MARGIN,
        y - 72 * mm,
        PAGE_W - 2 * MARGIN,
        63 * mm,
        max_value=5500,
        formatter=lambda value: f"{int(value):,}".replace(",", "."),
        accent=PURPLE,
    )
    y -= 82 * mm
    deviation_table_tr = [["Sapma", "Vaka"]] + [
        [
            f"{'beklenmeyen' if row.deviation_type == 'unexpected' else 'eksik' if row.deviation_type == 'missing' else 'tekrarlı'}: {row.activity}",
            f"{int(row.case_count):,}".replace(",", "."),
        ]
        for row in dev.itertuples()
    ]
    draw_table(c, deviation_table_tr, MARGIN, y, [130 * mm, 50 * mm], font_size=7.7)
    footer(c, 9, "reports/tables/variants.csv · deviations.csv")
    add_page(c)

    # 10 — Bottlenecks EN
    y = page_header(
        c,
        10,
        "Performance",
        "Bottlenecks, waiting and rework",
        "Elapsed time is concentrated in handoffs, not touch work",
    )
    metric_card(c, MARGIN, y - 30 * mm, 56 * mm, 27 * mm, "Wait share", "98.40%", "estimated", RED)
    metric_card(
        c,
        MARGIN + 61 * mm,
        y - 30 * mm,
        56 * mm,
        27 * mm,
        "Rework cases",
        "21.98%",
        "2,638 cases",
        AMBER,
    )
    metric_card(
        c,
        MARGIN + 122 * mm,
        y - 30 * mm,
        58 * mm,
        27 * mm,
        "Top bottleneck",
        "Goods",
        "0.924 score",
        BLUE,
    )
    y -= 39 * mm
    top_b = bottlenecks.head(7)
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "Composite bottleneck score")
    bar_chart(
        c,
        top_b["activity"].tolist(),
        top_b["bottleneck_score"].tolist(),
        MARGIN,
        y - 77 * mm,
        PAGE_W - 2 * MARGIN,
        68 * mm,
        max_value=1,
        formatter=lambda value: f"{value:.3f}",
        accent=BLUE,
    )
    y -= 88 * mm
    bullet_list(
        c,
        [
            "Goods Received accumulates 865,100 wait hours and affects every case.",
            "Delivery Delayed affects 1,551 cases with a p90 wait of 160.82 hours.",
            "Manager Approval is missing in 1,536 cases and repeated in 1,259 cases.",
            "The improvement program must protect control quality while reducing queue and handoff time.",
        ],
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        size=8.4,
    )
    footer(c, 10, "reports/tables/bottlenecks.csv · rework.csv")
    add_page(c)

    # 11 — Bottlenecks TR
    y = page_header(
        c,
        11,
        "Performans",
        "Darboğaz, bekleme ve yeniden işleme",
        "Geçen süre işlemden çok devirlerde yoğunlaşıyor",
    )
    metric_card(c, MARGIN, y - 30 * mm, 56 * mm, 27 * mm, "Bekleme payı", "%98,40", "tahmini", RED)
    metric_card(
        c,
        MARGIN + 61 * mm,
        y - 30 * mm,
        56 * mm,
        27 * mm,
        "Yeniden işleme",
        "%21,98",
        "2.638 vaka",
        AMBER,
    )
    metric_card(
        c,
        MARGIN + 122 * mm,
        y - 30 * mm,
        58 * mm,
        27 * mm,
        "En büyük darboğaz",
        "Mal kabul",
        "0,924 skor",
        BLUE,
    )
    y -= 39 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "Bileşik darboğaz skoru")
    bar_chart(
        c,
        [
            "Mal kabul",
            "Fatura alımı",
            "Teslimat gecikmesi",
            "Ödeme gerçekleştirme",
            "Ödeme yetkilendirme",
            "Yönetici onayı",
            "Satın alma inceleme",
        ],
        top_b["bottleneck_score"].tolist(),
        MARGIN,
        y - 77 * mm,
        PAGE_W - 2 * MARGIN,
        68 * mm,
        max_value=1,
        formatter=lambda value: f"{value:.3f}".replace(".", ","),
        accent=BLUE,
    )
    y -= 88 * mm
    bullet_list(
        c,
        [
            "Goods Received tüm vakaları etkileyen 865.100 saat toplam bekleme oluşturmaktadır.",
            "Delivery Delayed 1.551 vakada görülmekte ve p90 bekleme süresi 160,82 saattir.",
            "Manager Approval 1.536 vakada eksik, 1.259 vakada tekrarlıdır.",
            "İyileştirme; kontrol kalitesini korurken kuyruk ve devir süresini azaltmalıdır.",
        ],
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        size=8.4,
    )
    footer(c, 11, "reports/tables/bottlenecks.csv · rework.csv")
    add_page(c)

    # 12 — SLA model EN
    y = page_header(
        c,
        12,
        "Prediction",
        "Explainable SLA-risk model",
        "Features are cut at Purchase Order creation to limit leakage",
    )
    for index, args in enumerate(
        [
            ("Train", "9,600", "earliest cases", BLUE),
            ("Holdout", "2,400", "latest 20%", PURPLE),
            ("ROC AUC", "0.822", "discrimination", TEAL),
            ("Recall", "69.30%", "breach capture", AMBER),
        ]
    ):
        metric_card(c, MARGIN + index * (card_w + 3 * mm), y - 31 * mm, card_w, 27 * mm, *args)
    y -= 40 * mm
    steps = [
        ("1", "Event cut", "Only information available by PO creation"),
        ("2", "Features", "Amount, elapsed time, rework, organization, vendor and priority"),
        ("3", "Temporal split", "Earliest 80% train; latest 20% holdout"),
        ("4", "Score", "Logistic probability and four review bands"),
    ]
    step_w = (PAGE_W - 2 * MARGIN - 9 * mm) / 4
    for index, (number, name, text) in enumerate(steps):
        x = MARGIN + index * (step_w + 3 * mm)
        rounded_panel(c, x, y - 48 * mm, step_w, 44 * mm, fill=WHITE)
        c.setFillColor(BLUE)
        c.circle(x + 7 * mm, y - 12 * mm, 4 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("DejaVu-Bold", 8)
        c.drawCentredString(x + 7 * mm, y - 14 * mm, number)
        c.setFillColor(INK)
        c.setFont("DejaVu-Bold", 8.5)
        c.drawString(x + 14 * mm, y - 14 * mm, name)
        paragraph(c, text, x + 5 * mm, y - 23 * mm, step_w - 10 * mm, size=7.1, leading=10)
    y -= 59 * mm
    metrics = report["sla_prediction"]["metrics"]
    model_table = [
        ["Metric", "Holdout value", "Interpretation"],
        ["Average precision", f"{metrics['average_precision']:.3f}", "Positive-class ranking"],
        ["Accuracy", f"{metrics['accuracy']:.3f}", "Overall threshold accuracy"],
        ["Precision", f"{metrics['precision']:.3f}", "Share of alerts that breach"],
        ["Recall", f"{metrics['recall']:.3f}", "Share of breaches detected"],
        ["F1", f"{metrics['f1']:.3f}", "Precision/recall balance"],
        ["Brier score", f"{metrics['brier_score']:.3f}", "Probability error; lower is better"],
    ]
    draw_table(c, model_table, MARGIN, y, [55 * mm, 40 * mm, 85 * mm], font_size=7.7)
    footer(c, 12, "docs/sla-model-card.md · reports/demo-analysis.json")
    add_page(c)

    # 13 — SLA model TR
    y = page_header(
        c,
        13,
        "Tahmin",
        "Açıklanabilir SLA risk modeli",
        "Veri sızıntısını sınırlamak için özellikler PO oluşumunda kesilir",
    )
    for index, args in enumerate(
        [
            ("Eğitim", "9.600", "en eski vakalar", BLUE),
            ("Holdout", "2.400", "son %20", PURPLE),
            ("ROC AUC", "0,822", "ayırt etme", TEAL),
            ("Recall", "%69,30", "ihlal yakalama", AMBER),
        ]
    ):
        metric_card(c, MARGIN + index * (card_w + 3 * mm), y - 31 * mm, card_w, 27 * mm, *args)
    y -= 40 * mm
    steps_tr = [
        ("1", "Olay kesiti", "Yalnızca PO oluşumuna kadar bilinen bilgi"),
        ("2", "Özellikler", "Tutar, geçen süre, rework, organizasyon, tedarikçi ve öncelik"),
        ("3", "Zamansal bölme", "İlk %80 eğitim; son %20 holdout"),
        ("4", "Skor", "Lojistik olasılık ve dört inceleme bandı"),
    ]
    for index, (number, name, text) in enumerate(steps_tr):
        x = MARGIN + index * (step_w + 3 * mm)
        rounded_panel(c, x, y - 48 * mm, step_w, 44 * mm, fill=WHITE)
        c.setFillColor(BLUE)
        c.circle(x + 7 * mm, y - 12 * mm, 4 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("DejaVu-Bold", 8)
        c.drawCentredString(x + 7 * mm, y - 14 * mm, number)
        c.setFillColor(INK)
        c.setFont("DejaVu-Bold", 8.5)
        c.drawString(x + 14 * mm, y - 14 * mm, name)
        paragraph(c, text, x + 5 * mm, y - 23 * mm, step_w - 10 * mm, size=7.1, leading=10)
    y -= 59 * mm
    model_table_tr = [
        ["Metrik", "Holdout değeri", "Yorum"],
        [
            "Average precision",
            f"{metrics['average_precision']:.3f}".replace(".", ","),
            "Pozitif sınıf sıralaması",
        ],
        ["Accuracy", f"{metrics['accuracy']:.3f}".replace(".", ","), "Genel eşik doğruluğu"],
        ["Precision", f"{metrics['precision']:.3f}".replace(".", ","), "Uyarıların ihlal payı"],
        ["Recall", f"{metrics['recall']:.3f}".replace(".", ","), "Yakalanan ihlallerin payı"],
        ["F1", f"{metrics['f1']:.3f}".replace(".", ","), "Precision/recall dengesi"],
        [
            "Brier skoru",
            f"{metrics['brier_score']:.3f}".replace(".", ","),
            "Olasılık hatası; düşük daha iyi",
        ],
    ]
    draw_table(c, model_table_tr, MARGIN, y, [55 * mm, 40 * mm, 85 * mm], font_size=7.7)
    footer(c, 13, "docs/sla-model-card.md · reports/demo-analysis.json")
    add_page(c)

    # 14 — Simulation EN
    y = page_header(
        c,
        14,
        "Simulation",
        "What-if capacity simulation",
        "Paired scenario comparison with explicit assumptions",
    )
    section_box(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        "Method",
        "A six-stage finite-capacity queue network runs 24 replications × 900 cases for each scenario. Shared random seeds reduce comparison noise. Service and supplier lead times are lognormal; invoice rework is scenario-specific.",
        fill=BLUE_LIGHT,
        accent=BLUE,
        height=32 * mm,
    )
    y -= 41 * mm
    scenario_table = [["Scenario", "Mean cycle", "SLA", "Investment", "Annual value", "ROI"]]
    for row in scenarios.itertuples():
        scenario_table.append(
            [
                row.scenario,
                f"{row.mean_cycle_hours:.1f} h",
                f"{row.sla_adherence:.1%}",
                f"${row.one_time_investment_usd:,.0f}",
                f"${row.estimated_annual_value_usd:,.0f}",
                f"{row.first_year_roi:.2f}x",
            ]
        )
    draw_table(
        c,
        scenario_table,
        MARGIN,
        y,
        [43 * mm, 25 * mm, 21 * mm, 29 * mm, 36 * mm, 26 * mm],
        font_size=7.1,
    )
    y -= 48 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "SLA adherence by scenario")
    bar_chart(
        c,
        ["Baseline", "Approval automation", "AP capacity", "Combined"],
        scenarios["sla_adherence"].tolist(),
        MARGIN,
        y - 60 * mm,
        PAGE_W - 2 * MARGIN,
        51 * mm,
        max_value=0.85,
        formatter=lambda value: f"{value:.1%}",
        accent=AMBER,
    )
    y -= 70 * mm
    section_box(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        "Interpretation",
        "The simulator estimates operational potential; it does not prove causality. Replace all cost coefficients with Finance-owned values and measure a controlled pilot before funding or booking savings.",
        fill=RED_LIGHT,
        accent=RED,
        height=30 * mm,
    )
    footer(c, 14, "docs/simulation-methodology.md")
    add_page(c)

    # 15 — Simulation TR
    y = page_header(
        c,
        15,
        "Simülasyon",
        "What-if kapasite simülasyonu",
        "Açık varsayımlarla eşleştirilmiş senaryo karşılaştırması",
    )
    section_box(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        "Yöntem",
        "Altı aşamalı sonlu kapasite kuyruk ağı her senaryo için 24 tekrar × 900 vaka çalıştırır. Ortak rastgele seed'ler karşılaştırma gürültüsünü azaltır. Hizmet ve tedarikçi süreleri lognormal, fatura yeniden işleme oranı senaryoya özeldir.",
        fill=BLUE_LIGHT,
        accent=BLUE,
        height=32 * mm,
    )
    y -= 41 * mm
    scenario_table_tr = [["Senaryo", "Ort. çevrim", "SLA", "Yatırım", "Yıllık değer", "ROI"]]
    scenario_names_tr = [
        "Mevcut durum",
        "Onay otomasyonu",
        "AP kapasitesi",
        "Birleşik optimizasyon",
    ]
    for name, row in zip(scenario_names_tr, scenarios.itertuples(), strict=True):
        scenario_table_tr.append(
            [
                name,
                f"{row.mean_cycle_hours:.1f} s".replace(".", ","),
                f"%{row.sla_adherence * 100:.1f}".replace(".", ","),
                f"${row.one_time_investment_usd:,.0f}",
                f"${row.estimated_annual_value_usd:,.0f}",
                f"{row.first_year_roi:.2f}x".replace(".", ","),
            ]
        )
    draw_table(
        c,
        scenario_table_tr,
        MARGIN,
        y,
        [43 * mm, 25 * mm, 21 * mm, 29 * mm, 36 * mm, 26 * mm],
        font_size=7.1,
    )
    y -= 48 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "Senaryoya göre SLA uyumu")
    bar_chart(
        c,
        ["Mevcut durum", "Onay otomasyonu", "AP kapasitesi", "Birleşik"],
        scenarios["sla_adherence"].tolist(),
        MARGIN,
        y - 60 * mm,
        PAGE_W - 2 * MARGIN,
        51 * mm,
        max_value=0.85,
        formatter=lambda value: f"%{value * 100:.1f}".replace(".", ","),
        accent=AMBER,
    )
    y -= 70 * mm
    section_box(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        "Yorum",
        "Simülasyon operasyonel potansiyeli tahmin eder; nedenselliği kanıtlamaz. Finansman veya tasarruf kaydı öncesinde tüm maliyet katsayıları Finans tarafından güncellenmeli ve kontrollü pilot ölçülmelidir.",
        fill=RED_LIGHT,
        accent=RED,
        height=30 * mm,
    )
    footer(c, 15, "docs/simulation-methodology.md")
    add_page(c)

    # 16 — Recommendation EN
    y = page_header(
        c,
        16,
        "Decision",
        "Recommended combined optimization",
        "The strongest modeled outcome with explicit control gates",
    )
    combined = scenarios.iloc[-1]
    baseline = scenarios.iloc[0]
    for index, args in enumerate(
        [
            ("Cycle reduction", "19.42%", "40.12 h saved", BLUE),
            ("SLA uplift", "+13.63 pp", "77.64% modeled", TEAL),
            ("Annual value", "$2.21M", "synthetic", PURPLE),
            ("First-year ROI", "8.84x", "$225k investment", AMBER),
        ]
    ):
        metric_card(c, MARGIN + index * (card_w + 3 * mm), y - 31 * mm, card_w, 27 * mm, *args)
    cycle_value = (baseline.mean_cycle_hours - combined.mean_cycle_hours) * 5.5 * 8000
    manual_value = (baseline.manual_hours_per_case - combined.manual_hours_per_case) * 32 * 8000
    breach_value = (combined.sla_adherence - baseline.sla_adherence) * 85 * 8000
    y -= 42 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "Modeled annual value bridge")
    value_table = [
        ["Value component", "Formula", "Modeled value"],
        ["Delay-hour reduction", "40.12 h × $5.50 × 8,000", f"${cycle_value:,.0f}"],
        ["Manual-hour reduction", "1.39 h × $32 × 8,000", f"${manual_value:,.0f}"],
        ["Avoided breach value", "13.63% × $85 × 8,000", f"${breach_value:,.0f}"],
        ["Total", "Reconciled to pipeline", f"${combined.estimated_annual_value_usd:,.0f}"],
    ]
    draw_table(c, value_table, MARGIN, y - 8 * mm, [60 * mm, 72 * mm, 48 * mm], font_size=7.6)
    y -= 68 * mm
    actions = [
        (
            "Approval routing",
            "Automate assignment and low-risk routing; retain accountable approval and exception audit.",
            BLUE_LIGHT,
            BLUE,
        ),
        (
            "AP / Treasury capacity",
            "Add targeted invoice-match and payment-authorization capacity during the pilot window.",
            TEAL_LIGHT,
            TEAL,
        ),
        (
            "Supplier intervention",
            "Prioritize high-variance vendors and measure confirmation-to-receipt lead time.",
            AMBER_LIGHT,
            AMBER,
        ),
    ]
    for index, (name, text, fill, accent) in enumerate(actions):
        section_box(
            c,
            MARGIN + index * 62 * mm,
            y,
            57 * mm,
            name,
            text,
            fill=fill,
            accent=accent,
            height=45 * mm,
        )
    footer(c, 16, "reports/tables/simulation_scenarios.csv")
    add_page(c)

    # 17 — Recommendation TR
    y = page_header(
        c,
        17,
        "Karar",
        "Önerilen birleşik optimizasyon",
        "Açık kontrol kapılarıyla en güçlü modellenmiş sonuç",
    )
    for index, args in enumerate(
        [
            ("Çevrim azalması", "%19,42", "40,12 saat", BLUE),
            ("SLA artışı", "+13,63 puan", "%77,64 model", TEAL),
            ("Yıllık değer", "2,21M $", "sentetik", PURPLE),
            ("İlk yıl ROI", "8,84x", "225 bin $ yatırım", AMBER),
        ]
    ):
        metric_card(c, MARGIN + index * (card_w + 3 * mm), y - 31 * mm, card_w, 27 * mm, *args)
    y -= 42 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "Modellenmiş yıllık değer köprüsü")
    value_table_tr = [
        ["Değer bileşeni", "Formül", "Modellenmiş değer"],
        ["Bekleme saati azalması", "40,12 s × $5,50 × 8.000", f"${cycle_value:,.0f}"],
        ["Manuel saat azalması", "1,39 s × $32 × 8.000", f"${manual_value:,.0f}"],
        ["Önlenen ihlal değeri", "%13,63 × $85 × 8.000", f"${breach_value:,.0f}"],
        ["Toplam", "Pipeline ile mutabık", f"${combined.estimated_annual_value_usd:,.0f}"],
    ]
    draw_table(c, value_table_tr, MARGIN, y - 8 * mm, [60 * mm, 72 * mm, 48 * mm], font_size=7.6)
    y -= 68 * mm
    actions_tr = [
        (
            "Onay yönlendirme",
            "Atama ve düşük riskli yönlendirmeyi otomatikleştir; sorumlu onayı ve istisna izini koru.",
            BLUE_LIGHT,
            BLUE,
        ),
        (
            "AP / Hazine kapasitesi",
            "Pilot döneminde fatura eşleştirme ve ödeme yetkilendirme kapasitesini hedefli artır.",
            TEAL_LIGHT,
            TEAL,
        ),
        (
            "Tedarikçi müdahalesi",
            "Yüksek varyanslı tedarikçileri önceliklendir ve teyit-mal kabul süresini ölç.",
            AMBER_LIGHT,
            AMBER,
        ),
    ]
    for index, (name, text, fill, accent) in enumerate(actions_tr):
        section_box(
            c,
            MARGIN + index * 62 * mm,
            y,
            57 * mm,
            name,
            text,
            fill=fill,
            accent=accent,
            height=45 * mm,
        )
    footer(c, 17, "reports/tables/simulation_scenarios.csv")
    add_page(c)

    # 18 — Architecture & governance
    y = page_header(
        c,
        18,
        "Platform",
        "Architecture & governance",
        "Mimari ve yönetişim · Reproducible evidence with a read-only decision boundary",
    )
    rounded_panel(c, MARGIN, y - 109 * mm, PAGE_W - 2 * MARGIN, 109 * mm)
    image_fit(
        c,
        ROOT / "docs/images/architecture.png",
        MARGIN + 3 * mm,
        y - 107 * mm,
        PAGE_W - 2 * MARGIN - 6 * mm,
        104 * mm,
    )
    y -= 118 * mm
    governance_table = [
        ["Control / Kontrol", "Implementation / Uygulama"],
        [
            "Read-only decision API",
            "No transaction mutation endpoints / İşlem değiştiren endpoint yok",
        ],
        ["Human in the loop", "Review prioritization only / Yalnızca inceleme önceliği"],
        [
            "Reproducible evidence",
            "Fixed seed, contracts, CI drift check / Sabit seed ve sözleşmeler",
        ],
        ["Security baseline", "Nonroot image, CodeQL, Trivy, least privilege"],
        ["Model governance", "Temporal holdout, model card, rollback runbook"],
    ]
    draw_table(c, governance_table, MARGIN, y, [58 * mm, 122 * mm], font_size=7.5)
    footer(c, 18, "docs/architecture.md · docs/security-threat-model.md")
    add_page(c)

    # 19 — Roadmap
    y = page_header(
        c,
        19,
        "Roadmap",
        "90-day roadmap / 90 günlük yol haritası",
        "Pilot before scale · Ölç, doğrula, sonra ölçekle",
    )
    phases = [
        (
            "0–30 DAYS / GÜN",
            "Calibrate / Kalibre et",
            [
                "Confirm KPI definitions and process owners.",
                "Replace synthetic cost coefficients with Finance values.",
                "Validate source-system timestamps and event completeness.",
                "Pre-register pilot baseline and control metrics.",
            ],
            BLUE_LIGHT,
            BLUE,
        ),
        (
            "31–60 DAYS / GÜN",
            "Pilot / Pilotla",
            [
                "Route low-risk approvals with human accountability.",
                "Add temporary AP/treasury capacity to selected queues.",
                "Prioritize high-variance suppliers.",
                "Track SLA, rework, wait, control exceptions and workload.",
            ],
            TEAL_LIGHT,
            TEAL,
        ),
        (
            "61–90 DAYS / GÜN",
            "Decide / Karar ver",
            [
                "Compare pilot and control cohorts.",
                "Recalculate value using observed effects.",
                "Review fairness, control quality and unintended outcomes.",
                "Scale, revise or stop through an accountable gate.",
            ],
            AMBER_LIGHT,
            AMBER,
        ),
    ]
    phase_h = 64 * mm
    for index, (period, name, items, fill, accent) in enumerate(phases):
        x = MARGIN + index * 62 * mm
        rounded_panel(c, x, y - phase_h, 57 * mm, phase_h, fill=fill)
        c.setFillColor(accent)
        c.setFont("DejaVu-Bold", 7.2)
        c.drawString(x + 5 * mm, y - 9 * mm, period)
        c.setFillColor(INK)
        c.setFont("DejaVu-Bold", 12)
        c.drawString(x + 5 * mm, y - 18 * mm, name)
        bullet_list(c, items, x + 5 * mm, y - 27 * mm, 47 * mm, size=6.8, gap=2.2 * mm)
    y -= 76 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(MARGIN, y, "Decision gates / Karar kapıları")
    gate_table = [
        ["Gate", "Evidence required / Gerekli kanıt", "Owner / Sorumlu"],
        ["Data ready", "Reconciled events and approved KPI catalog", "Data + Process Owner"],
        [
            "Pilot ready",
            "Control design, rollback, baseline and sample",
            "Operations + Internal Control",
        ],
        [
            "Scale ready",
            "Observed effect, calibrated value, no control regression",
            "Steering Committee",
        ],
    ]
    draw_table(c, gate_table, MARGIN, y - 8 * mm, [34 * mm, 104 * mm, 42 * mm], font_size=7.2)
    footer(c, 19, "ROADMAP.md · docs/deployment.md")
    add_page(c)

    # 20 — Evidence, limitations, sources
    y = page_header(
        c,
        20,
        "Evidence",
        "Validation, limitations & sources",
        "What is proven, what remains hypothetical / Kanıt ve sınırlar",
    )
    validation = [
        ["Acceptance gate / Kabul kapısı", "Result / Sonuç"],
        ["Automated tests", "58 passed"],
        ["Coverage", "96.97%"],
        ["Event/case reconciliation", "Passed"],
        ["Duplicate keys / required nulls", "0 / 0"],
        ["PM4Py reference discovery", "Passed"],
        ["PDF pages / PPTX slides / XLSX sheets", "20 / 20 / 8"],
    ]
    draw_table(c, validation, MARGIN, y, [106 * mm, 74 * mm], font_size=7.4)
    y -= 61 * mm
    section_box(
        c,
        MARGIN,
        y,
        87 * mm,
        "Limitations / Sınırlamalar",
        "Synthetic data does not establish real-world impact. The model is not production calibrated. Simulation assumptions are not causal evidence. Power BI Desktop and Docker execution require downstream environment validation.",
        fill=RED_LIGHT,
        accent=RED,
        height=45 * mm,
    )
    section_box(
        c,
        MARGIN + 93 * mm,
        y,
        87 * mm,
        "Responsible use / Sorumlu kullanım",
        "Use scores to prioritize review, preserve segregation of duties, monitor subgroup errors, validate cost assumptions with Finance, and scale only after a measured pilot.",
        fill=TEAL_LIGHT,
        accent=TEAL,
        height=45 * mm,
    )
    y -= 55 * mm
    c.setFillColor(INK)
    c.setFont("DejaVu-Bold", 10)
    c.drawString(MARGIN, y, "Primary technical sources / Birincil teknik kaynaklar")
    source_items = [
        "PM4Py features & API — processintelligence.solutions/pm4py",
        "BPMN 2.0.2 — omg.org/spec/BPMN/2.0.2",
        "Power BI Projects — learn.microsoft.com/power-bi/developer/projects",
        "FastAPI — fastapi.tiangolo.com",
        "PostgreSQL 17 — postgresql.org/docs/17",
        "scikit-learn LogisticRegression — scikit-learn.org",
    ]
    bullet_list(c, source_items, MARGIN, y - 8 * mm, PAGE_W - 2 * MARGIN, size=7.2, gap=2.5 * mm)
    c.setFillColor(NAVY)
    c.roundRect(MARGIN, 20 * mm, PAGE_W - 2 * MARGIN, 22 * mm, 4 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("DejaVu-Bold", 10)
    c.drawString(MARGIN + 7 * mm, 33 * mm, "Murat Miraç Gedik")
    c.setFont("DejaVu", 7.2)
    c.drawString(
        MARGIN + 7 * mm,
        26 * mm,
        "Business/Data Analyst portfolio · GitHub: muratmiracg-dev",
    )
    c.drawRightString(
        PAGE_W - MARGIN - 7 * mm,
        29 * mm,
        "Full source list / Tam kaynakça: docs/sources.md",
    )
    footer(c, 20, "docs/validation.md · docs/sources.md")
    c.save()


if __name__ == "__main__":
    build()
