from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from .models import DocumentContent
from .styles import DocumentStyle


def _load_font(candidates: tuple[str, ...], size: int) -> ImageFont.ImageFont:
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _measure_text(font: ImageFont.ImageFont, value: str) -> int:
    left, _, right, _ = font.getbbox(value or " ")
    return right - left


def _wrap_text_pixels(font: ImageFont.ImageFont, value: str, max_width: int) -> list[str]:
    if not value:
        return []
    words = value.split()
    if not words:
        return [value]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if _measure_text(font, trial) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _pdf_wrap(value: str, font_name: str, font_size: int, max_width: float) -> list[str]:
    if not value:
        return []
    return simpleSplit(value, font_name, font_size, max_width)


def _lighten(color: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    return tuple(min(255, channel + amount) for channel in color)


def _supplier_initials(document: DocumentContent) -> str:
    tokens = [chunk for chunk in document.supplier.company_name.replace("-", " ").split() if chunk]
    if not tokens:
        return "FD"
    initials = "".join(token[0].upper() for token in tokens[:3])
    return initials[:3]


def _draw_background(draw: ImageDraw.ImageDraw, width: int, height: int, style: DocumentStyle) -> None:
    pattern_color = _lighten(style.border_color, 30)

    if style.background_pattern == "grid":
        for x in range(70, width, 120):
            draw.line((x, 0, x, height), fill=pattern_color, width=1)
        for y in range(70, height, 120):
            draw.line((0, y, width, y), fill=pattern_color, width=1)
    elif style.background_pattern == "dots":
        for x in range(80, width, 110):
            for y in range(80, height, 110):
                draw.ellipse((x, y, x + 5, y + 5), fill=pattern_color)
    elif style.background_pattern == "diagonal":
        for offset in range(-height, width, 110):
            draw.line((offset, 0, offset + height, height), fill=pattern_color, width=2)
    elif style.background_pattern == "thin_lines":
        for y in range(90, height, 80):
            draw.line((60, y, width - 60, y), fill=pattern_color, width=1)


def _draw_header(
    draw: ImageDraw.ImageDraw, width: int, style: DocumentStyle, document: DocumentContent, title_font: ImageFont.ImageFont, badge_font: ImageFont.ImageFont
) -> int:
    initials = _supplier_initials(document)
    title_y = 78

    if style.header_layout == "band":
        draw.rectangle((0, 0, width, 190), fill=style.title_color)
        draw.rounded_rectangle((78, 50, 198, 170), radius=26, fill=style.accent_color)
        draw.text((108, 86), initials, fill="white", font=badge_font)
        draw.text((240, title_y), document.title, fill="white", font=title_font)
        draw.rounded_rectangle((width - 330, 56, width - 86, 124), radius=28, fill="white")
        draw.text((width - 296, 78), style.badge_text, fill=style.title_color, font=badge_font)
        return 240

    if style.header_layout == "boxed":
        draw.rounded_rectangle((55, 40, width - 55, 215), radius=36, fill=style.panel_color, outline=style.border_color, width=4)
        draw.rounded_rectangle((78, 66, 198, 186), radius=26, fill=style.title_color)
        draw.text((108, 102), initials, fill="white", font=badge_font)
        draw.text((240, title_y + 8), document.title, fill=style.title_color, font=title_font)
        draw.rounded_rectangle((width - 318, 74, width - 92, 132), radius=24, fill=style.accent_color)
        draw.text((width - 285, 92), style.badge_text, fill="white", font=badge_font)
        return 255

    if style.header_layout == "ribbon":
        draw.polygon([(0, 0), (width, 0), (width, 150), (width - 160, 210), (0, 210)], fill=style.title_color)
        draw.rectangle((72, 54, 204, 174), fill="white")
        draw.text((105, 92), initials, fill=style.title_color, font=badge_font)
        draw.text((250, title_y), document.title, fill="white", font=title_font)
        draw.rounded_rectangle((width - 300, 58, width - 88, 122), radius=22, fill=style.accent_color)
        draw.text((width - 270, 78), style.badge_text, fill="white", font=badge_font)
        return 248

    if style.header_layout == "sidebar":
        draw.rectangle((0, 0, 120, 2339), fill=style.title_color)
        draw.ellipse((24, 40, 96, 112), fill="white")
        draw.text((36, 66), initials[:2], fill=style.title_color, font=badge_font)
        draw.text((160, title_y), document.title, fill=style.title_color, font=title_font)
        draw.rounded_rectangle((width - 328, 52, width - 94, 116), radius=24, fill=style.panel_color, outline=style.border_color, width=3)
        draw.text((width - 298, 72), style.badge_text, fill=style.title_color, font=badge_font)
        return 205

    draw.rectangle((0, 0, width, 120), fill=style.title_color)
    draw.rectangle((0, 120, width, 220), fill=style.panel_color)
    draw.rectangle((70, 48, 190, 168), fill=style.accent_color)
    draw.text((98, 86), initials, fill="white", font=badge_font)
    draw.text((238, title_y), document.title, fill="white", font=title_font)
    draw.rounded_rectangle((width - 332, 136, width - 88, 196), radius=22, fill=style.accent_color)
    draw.text((width - 298, 154), style.badge_text, fill="white", font=badge_font)
    return 255


def _draw_section_box(
    draw: ImageDraw.ImageDraw,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    style: DocumentStyle,
    title: str,
    title_font: ImageFont.ImageFont,
) -> None:
    draw.rounded_rectangle((x1, y1, x2, y2), radius=24, fill=style.panel_color, outline=style.border_color, width=3)
    draw.rounded_rectangle((x1 + 18, y1 - 16, x1 + 240, y1 + 26), radius=18, fill=style.accent_color)
    draw.text((x1 + 34, y1 - 6), title, fill="white", font=title_font)


def render_document_image(document: DocumentContent, output_path: Path, width: int, height: int, style: DocumentStyle) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (width, height), color=style.page_color)
    draw = ImageDraw.Draw(image)

    _draw_background(draw, width, height, style)

    title_font = _load_font(style.image_fonts, 42)
    subtitle_font = _load_font(style.image_fonts, 24)
    body_font = _load_font(style.image_fonts, 22)
    badge_font = _load_font(style.image_fonts, 26)

    y = _draw_header(draw, width, style, document, title_font, badge_font)

    sections = [
        ("Fournisseur", [document.supplier.company_name, *document.supplier.address_lines(), f"SIRET {document.supplier.siret}", f"TVA {document.supplier.vat_number}"]),
        ("Client", [document.customer.company_name, *document.customer.address_lines(), f"SIRET {document.customer.siret}"]),
        (
            "Reference",
            [
                f"Facture: {document.invoice_number}" if document.invoice_number else "",
                f"Devis: {document.quote_number}" if document.quote_number else "",
                f"Attestation: {document.attestation_reference}" if document.attestation_reference else "",
                f"Date emission: {document.issue_date}" if document.issue_date else "",
                f"Date echeance: {document.due_date}" if document.due_date else "",
                f"Date expiration: {document.expiration_date}" if document.expiration_date else "",
            ],
        ),
    ]

    for section_title, lines in sections:
        line_count = sum(max(1, len(_wrap_text_pixels(body_font, line, width - 360))) for line in lines if line)
        box_height = 58 + (line_count * 30)
        _draw_section_box(draw, 120, y, width - 120, y + box_height, style, section_title, subtitle_font)
        current_y = y + 36
        for line in [entry for entry in lines if entry]:
            for wrapped in _wrap_text_pixels(body_font, line, width - 360):
                draw.text((154, current_y), wrapped, fill=style.title_color, font=body_font)
                current_y += 30
        y += box_height + 30

    if document.doc_type in {"invoice", "quote"}:
        table_height = 150
        wrapped_line_items: list[list[str]] = []
        for item in document.line_items:
            wrapped_desc = _wrap_text_pixels(body_font, str(item["description"]), 820)
            wrapped_line_items.append(wrapped_desc)
            table_height += 22 + (len(wrapped_desc) * 28)
        _draw_section_box(draw, 120, y, width - 120, y + table_height, style, "Prestations", subtitle_font)
        headers = ["Description", "Qt", "PU", "Total"]
        columns = [150, 1030, 1180, 1350]
        current_y = y + 44
        draw.rounded_rectangle((140, current_y - 4, width - 140, current_y + 36), radius=14, fill=_lighten(style.accent_color, 20))
        for column, header in zip(columns, headers, strict=True):
            draw.text((column, current_y), header, fill="white", font=body_font)
        current_y += 54

        for item, wrapped_description in zip(document.line_items, wrapped_line_items, strict=True):
            row_height = max(40, 18 + len(wrapped_description) * 28)
            draw.rounded_rectangle((140, current_y - 8, width - 140, current_y + row_height - 6), radius=10, fill="white", outline=style.border_color, width=1)
            desc_y = current_y
            for wrapped in wrapped_description:
                draw.text((columns[0], desc_y), wrapped, fill=style.title_color, font=body_font)
                desc_y += 26
            draw.text((columns[1], current_y), str(item["quantity"]), fill=style.title_color, font=body_font)
            draw.text((columns[2], current_y), f"{item['unit_price']:.2f}", fill=style.title_color, font=body_font)
            draw.text((columns[3], current_y), f"{item['line_total']:.2f}", fill=style.title_color, font=body_font)
            current_y += row_height + 6

        totals_y = current_y + 10
        for line in [
            f"Montant HT: {document.amount_ht:.2f} {document.currency}",
            f"TVA: {document.amount_tva:.2f} {document.currency}",
            f"Montant TTC: {document.amount_ttc:.2f} {document.currency}",
        ]:
            draw.text((width - 560, totals_y), line, fill=style.title_color, font=subtitle_font)
            totals_y += 38
        y += table_height + 30

    if document.doc_type == "rib":
        _draw_section_box(draw, 120, y, width - 120, y + 170, style, "Coordonnees bancaires", subtitle_font)
        current_y = y + 42
        for line in [f"IBAN: {document.iban}", f"BIC: {document.bic}"]:
            draw.text((154, current_y), line, fill=style.title_color, font=body_font)
            current_y += 34
        y += 200

    if document.notes:
        wrapped_notes = [_wrap_text_pixels(body_font, note, width - 360) for note in document.notes]
        note_height = 70 + sum(len(note_lines) * 28 for note_lines in wrapped_notes)
        _draw_section_box(draw, 120, y, width - 120, y + note_height, style, "Notes", subtitle_font)
        current_y = y + 40
        for note_lines in wrapped_notes:
            for wrapped in note_lines:
                draw.text((154, current_y), wrapped, fill=style.muted_color, font=body_font)
                current_y += 28

    footer_y = height - 94
    draw.line((120, footer_y, width - 120, footer_y), fill=style.border_color, width=2)
    draw.text((124, footer_y + 18), style.footer_text, fill=style.muted_color, font=body_font)
    image.save(output_path)


def _rgb(color: tuple[int, int, int]) -> tuple[float, float, float]:
    return tuple(channel / 255 for channel in color)


def _draw_pdf_background(pdf: canvas.Canvas, width: float, height: float, style: DocumentStyle) -> None:
    pdf.setFillColorRGB(*_rgb(style.page_color))
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setStrokeColorRGB(*_rgb(_lighten(style.border_color, 20)))

    if style.background_pattern == "grid":
        for x in range(25, int(width), 35):
            pdf.line(x * mm / 3.5, 0, x * mm / 3.5, height)
        for y in range(25, int(height), 35):
            pdf.line(0, y * mm / 3.5, width, y * mm / 3.5)
    elif style.background_pattern == "dots":
        for x in range(35, int(width), 70):
            for y in range(35, int(height), 70):
                pdf.circle(x * mm / 3.5, y * mm / 3.5, 1, stroke=0, fill=1)
    elif style.background_pattern == "diagonal":
        for offset in range(-200, int(width), 60):
            pdf.line(offset, 0, offset + height * 0.6, height)
    elif style.background_pattern == "thin_lines":
        for y in range(40, int(height), 30):
            pdf.line(18 * mm, y * mm / 3.5, width - 18 * mm, y * mm / 3.5)


def _draw_pdf_header(pdf: canvas.Canvas, width: float, height: float, style: DocumentStyle, document: DocumentContent) -> float:
    initials = _supplier_initials(document)
    pdf.setFont(style.pdf_title_font, 18)

    if style.header_layout == "band":
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.rect(0, height - 48 * mm, width, 48 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(*_rgb(style.accent_color))
        pdf.roundRect(18 * mm, height - 42 * mm, 26 * mm, 26 * mm, 5 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont(style.pdf_title_font, 14)
        pdf.drawString(24 * mm, height - 31 * mm, initials)
        pdf.setFont(style.pdf_title_font, 18)
        pdf.drawString(52 * mm, height - 28 * mm, document.title)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.roundRect(width - 60 * mm, height - 34 * mm, 40 * mm, 14 * mm, 4 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.drawString(width - 54 * mm, height - 28 * mm, style.badge_text)
        return height - 60 * mm

    if style.header_layout == "boxed":
        pdf.setFillColorRGB(*_rgb(style.panel_color))
        pdf.setStrokeColorRGB(*_rgb(style.border_color))
        pdf.roundRect(14 * mm, height - 56 * mm, width - 28 * mm, 38 * mm, 7 * mm, stroke=1, fill=1)
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.roundRect(20 * mm, height - 48 * mm, 24 * mm, 24 * mm, 4 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont(style.pdf_title_font, 14)
        pdf.drawString(26 * mm, height - 34 * mm, initials)
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.setFont(style.pdf_title_font, 18)
        pdf.drawString(50 * mm, height - 32 * mm, document.title)
        pdf.setFillColorRGB(*_rgb(style.accent_color))
        pdf.roundRect(width - 56 * mm, height - 42 * mm, 34 * mm, 12 * mm, 3 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont(style.pdf_body_font, 10)
        pdf.drawString(width - 50 * mm, height - 35 * mm, style.badge_text)
        return height - 66 * mm

    if style.header_layout == "ribbon":
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.rect(0, height - 52 * mm, width, 42 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.rect(18 * mm, height - 44 * mm, 22 * mm, 22 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.setFont(style.pdf_title_font, 14)
        pdf.drawString(23 * mm, height - 31 * mm, initials)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont(style.pdf_title_font, 18)
        pdf.drawString(48 * mm, height - 29 * mm, document.title)
        pdf.setFillColorRGB(*_rgb(style.accent_color))
        pdf.roundRect(width - 52 * mm, height - 41 * mm, 30 * mm, 12 * mm, 3 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont(style.pdf_body_font, 10)
        pdf.drawString(width - 47 * mm, height - 34 * mm, style.badge_text)
        return height - 62 * mm

    if style.header_layout == "sidebar":
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.rect(0, 0, 16 * mm, height, stroke=0, fill=1)
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.setFont(style.pdf_title_font, 18)
        pdf.drawString(24 * mm, height - 24 * mm, document.title)
        pdf.setFillColorRGB(*_rgb(style.panel_color))
        pdf.setStrokeColorRGB(*_rgb(style.border_color))
        pdf.roundRect(width - 58 * mm, height - 33 * mm, 36 * mm, 12 * mm, 3 * mm, stroke=1, fill=1)
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.setFont(style.pdf_body_font, 10)
        pdf.drawString(width - 52 * mm, height - 26 * mm, style.badge_text)
        return height - 48 * mm

    pdf.setFillColorRGB(*_rgb(style.title_color))
    pdf.rect(0, height - 32 * mm, width, 32 * mm, stroke=0, fill=1)
    pdf.setFillColorRGB(*_rgb(style.panel_color))
    pdf.rect(0, height - 54 * mm, width, 22 * mm, stroke=0, fill=1)
    pdf.setFillColorRGB(*_rgb(style.accent_color))
    pdf.rect(18 * mm, height - 43 * mm, 22 * mm, 22 * mm, stroke=0, fill=1)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont(style.pdf_title_font, 14)
    pdf.drawString(23 * mm, height - 30 * mm, initials)
    pdf.setFont(style.pdf_title_font, 18)
    pdf.drawString(48 * mm, height - 23 * mm, document.title)
    pdf.setFillColorRGB(*_rgb(style.accent_color))
    pdf.roundRect(width - 58 * mm, height - 49 * mm, 36 * mm, 12 * mm, 3 * mm, stroke=0, fill=1)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont(style.pdf_body_font, 10)
    pdf.drawString(width - 52 * mm, height - 42 * mm, style.badge_text)
    return height - 62 * mm


def render_document_pdf(document: DocumentContent, output_path: Path, style: DocumentStyle) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    _draw_pdf_background(pdf, width, height, style)
    y = _draw_pdf_header(pdf, width, height, style, document)

    sections = [
        ("Fournisseur", [document.supplier.company_name, *document.supplier.address_lines(), f"SIRET {document.supplier.siret}", f"TVA {document.supplier.vat_number}"]),
        ("Client", [document.customer.company_name, *document.customer.address_lines(), f"SIRET {document.customer.siret}"]),
        (
            "Reference",
            [
                f"Facture: {document.invoice_number}" if document.invoice_number else "",
                f"Devis: {document.quote_number}" if document.quote_number else "",
                f"Attestation: {document.attestation_reference}" if document.attestation_reference else "",
                f"Date emission: {document.issue_date}" if document.issue_date else "",
                f"Date echeance: {document.due_date}" if document.due_date else "",
                f"Date expiration: {document.expiration_date}" if document.expiration_date else "",
            ],
        ),
    ]

    for title, lines in sections:
        wrapped_lines: list[str] = []
        for line in [entry for entry in lines if entry]:
            wrapped_lines.extend(_pdf_wrap(line, style.pdf_body_font, 10, width - 60 * mm))
        box_height = max(18 * mm, 7 * mm + len(wrapped_lines) * 4.8 * mm)
        pdf.setFillColorRGB(*_rgb(style.panel_color))
        pdf.setStrokeColorRGB(*_rgb(style.border_color))
        pdf.roundRect(18 * mm, y - box_height, width - 36 * mm, box_height, 4 * mm, stroke=1, fill=1)
        pdf.setFillColorRGB(*_rgb(style.accent_color))
        pdf.roundRect(22 * mm, y - 4 * mm, 35 * mm, 7 * mm, 2 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont(style.pdf_body_font, 10)
        pdf.drawString(26 * mm, y - 0.8 * mm, title)
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.setFont(style.pdf_body_font, 10)
        text_y = y - 9 * mm
        for line in wrapped_lines:
            pdf.drawString(24 * mm, text_y, line)
            text_y -= 4.8 * mm
        y = text_y - 4 * mm

    if document.doc_type in {"invoice", "quote"}:
        wrapped_rows = []
        row_count = 0
        for item in document.line_items:
            desc_lines = _pdf_wrap(str(item["description"]), style.pdf_body_font, 9, 82 * mm)
            wrapped_rows.append((item, desc_lines))
            row_count += max(1, len(desc_lines))
        table_height = max(38 * mm, 12 * mm + row_count * 5.2 * mm + 18 * mm)
        pdf.setFillColorRGB(*_rgb(style.panel_color))
        pdf.setStrokeColorRGB(*_rgb(style.border_color))
        pdf.roundRect(18 * mm, y - table_height, width - 36 * mm, table_height, 4 * mm, stroke=1, fill=1)
        pdf.setFillColorRGB(*_rgb(style.accent_color))
        pdf.roundRect(22 * mm, y - 4 * mm, 32 * mm, 7 * mm, 2 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont(style.pdf_body_font, 10)
        pdf.drawString(26 * mm, y - 0.8 * mm, "Prestations")
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.setFont(style.pdf_body_font, 9)
        text_y = y - 10 * mm
        for item, desc_lines in wrapped_rows:
            first = True
            for desc_line in desc_lines:
                pdf.drawString(24 * mm, text_y, desc_line)
                if first:
                    pdf.drawString(111 * mm, text_y, str(item["quantity"]))
                    pdf.drawString(128 * mm, text_y, f"{item['unit_price']:.2f}")
                    pdf.drawString(156 * mm, text_y, f"{item['line_total']:.2f}")
                    first = False
                text_y -= 4.8 * mm
        for line in [
            f"Montant HT: {document.amount_ht:.2f} {document.currency}",
            f"TVA: {document.amount_tva:.2f} {document.currency}",
            f"Montant TTC: {document.amount_ttc:.2f} {document.currency}",
        ]:
            pdf.drawString(24 * mm, text_y - 1 * mm, line)
            text_y -= 4.6 * mm
        y = text_y - 3 * mm

    if document.doc_type == "rib":
        pdf.setFillColorRGB(*_rgb(style.panel_color))
        pdf.setStrokeColorRGB(*_rgb(style.border_color))
        pdf.roundRect(18 * mm, y - 20 * mm, width - 36 * mm, 20 * mm, 4 * mm, stroke=1, fill=1)
        pdf.setFillColorRGB(*_rgb(style.accent_color))
        pdf.roundRect(22 * mm, y - 4 * mm, 56 * mm, 7 * mm, 2 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont(style.pdf_body_font, 10)
        pdf.drawString(26 * mm, y - 0.8 * mm, "Coordonnees bancaires")
        pdf.setFillColorRGB(*_rgb(style.title_color))
        pdf.drawString(24 * mm, y - 10 * mm, f"IBAN: {document.iban}")
        pdf.drawString(24 * mm, y - 15 * mm, f"BIC: {document.bic}")
        y -= 25 * mm

    if document.notes:
        wrapped_notes: list[str] = []
        for note in document.notes:
            wrapped_notes.extend(_pdf_wrap(note, style.pdf_body_font, 10, width - 60 * mm))
        note_box_height = max(18 * mm, 7 * mm + len(wrapped_notes) * 4.8 * mm)
        pdf.setFillColorRGB(*_rgb(style.panel_color))
        pdf.setStrokeColorRGB(*_rgb(style.border_color))
        pdf.roundRect(18 * mm, y - note_box_height, width - 36 * mm, note_box_height, 4 * mm, stroke=1, fill=1)
        pdf.setFillColorRGB(*_rgb(style.accent_color))
        pdf.roundRect(22 * mm, y - 4 * mm, 20 * mm, 7 * mm, 2 * mm, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont(style.pdf_body_font, 10)
        pdf.drawString(26 * mm, y - 0.8 * mm, "Notes")
        pdf.setFillColorRGB(*_rgb(style.muted_color))
        text_y = y - 10 * mm
        for note in wrapped_notes:
            pdf.drawString(24 * mm, text_y, note)
            text_y -= 4.8 * mm

    pdf.setStrokeColorRGB(*_rgb(style.border_color))
    pdf.line(18 * mm, 16 * mm, width - 18 * mm, 16 * mm)
    pdf.setFillColorRGB(*_rgb(style.muted_color))
    pdf.setFont(style.pdf_body_font, 9)
    pdf.drawString(18 * mm, 10 * mm, style.footer_text)
    pdf.showPage()
    pdf.save()


def post_process_image(path: Path) -> None:
    image = Image.open(path)
    image = ImageEnhance.Sharpness(image).enhance(1.05)
    image = image.filter(ImageFilter.SMOOTH)
    image.save(path)
