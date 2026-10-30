"""Unicode PDF fonts with Bengali shaping (ReportLab + uharfbuzz).

Root cause of broken Bangla PDFs: ReportLab default Helvetica has no Bengali
glyphs and no Indic shaping. This module registers OFL Noto Sans Bengali and
provides ParagraphStyles that embed the font with HarfBuzz shaping.

Noto Sans Bengali does not include Latin letters, so mixed EN/BN strings are
split into script runs: Latin → Helvetica, Bengali → Noto Sans Bengali.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings

FONT_FAMILY = "NotoSansBengali"
FONT_FAMILY_BOLD = "NotoSansBengali-Bold"
LATIN_FONT = "Helvetica"
LATIN_FONT_BOLD = "Helvetica-Bold"

_REGISTERED = False

# Bengali block + common ZWJ/ZWNJ used in conjuncts.
_BN_CHAR = re.compile(r"[\u0980-\u09FF\u200C\u200D]")


def font_paths() -> tuple[Path, Path]:
    base = Path(settings.BASE_DIR) / "static" / "fonts"
    regular = base / "NotoSansBengali-Regular.ttf"
    bold = base / "NotoSansBengali-Bold.ttf"
    return regular, bold


def ensure_pdf_fonts() -> str:
    """Register Bengali-capable TTF fonts once. Returns regular font name."""
    global _REGISTERED
    if _REGISTERED:
        return FONT_FAMILY

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular, bold = font_paths()
    if not regular.is_file():
        raise FileNotFoundError(
            f"Bengali PDF font missing: {regular}. "
            "Expected OFL Noto Sans Bengali under static/fonts/."
        )
    pdfmetrics.registerFont(TTFont(FONT_FAMILY, str(regular)))
    if bold.is_file():
        pdfmetrics.registerFont(TTFont(FONT_FAMILY_BOLD, str(bold)))
    else:
        pdfmetrics.registerFont(TTFont(FONT_FAMILY_BOLD, str(regular)))
    _REGISTERED = True
    return FONT_FAMILY


@lru_cache(maxsize=1)
def shaping_available() -> bool:
    try:
        import uharfbuzz  # noqa: F401
        from reportlab.pdfbase.ttfonts import shapeStr

        ensure_pdf_fonts()
        shaped = shapeStr("বাংলা", FONT_FAMILY, 12)
        return shaped is not None and len(str(shaped)) > 0
    except Exception:
        return False


def pdf_paragraph_styles():
    """Return common ParagraphStyles using the embedded Bengali font."""
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    ensure_pdf_fonts()
    base = getSampleStyleSheet()
    # ReportLab disables Indic shaping unless style.shaping is truthy.
    title = ParagraphStyle(
        "ZFPdfTitle",
        parent=base["Title"],
        fontName=FONT_FAMILY_BOLD,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0B6B3A"),
        spaceAfter=10,
        shaping=1,
    )
    heading = ParagraphStyle(
        "ZFPdfHeading",
        parent=base["Heading1"],
        fontName=FONT_FAMILY_BOLD,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0B6B3A"),
        spaceAfter=6,
        shaping=1,
    )
    body = ParagraphStyle(
        "ZFPdfBody",
        parent=base["Normal"],
        fontName=FONT_FAMILY,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#111111"),
        shaping=1,
    )
    small = ParagraphStyle(
        "ZFPdfSmall",
        parent=body,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#555555"),
        shaping=1,
    )
    label = ParagraphStyle(
        "ZFPdfLabel",
        parent=body,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#666666"),
        shaping=1,
    )
    return {
        "title": title,
        "heading": heading,
        "body": body,
        "small": small,
        "label": label,
        "font": FONT_FAMILY,
        "font_bold": FONT_FAMILY_BOLD,
    }


def escape_pdf_text(value, *, bold: bool = False) -> str:
    """Escape text and wrap script runs for mixed EN/BN Paragraph markup."""
    text = str(value or "")
    if not text:
        return ""
    ensure_pdf_fonts()
    bn_font = FONT_FAMILY_BOLD if bold else FONT_FAMILY
    latin_font = LATIN_FONT_BOLD if bold else LATIN_FONT
    parts = []
    buf = []
    mode = None  # "bn" | "latin"

    def flush():
        nonlocal buf, mode
        if not buf:
            return
        chunk = "".join(buf)
        buf = []
        escaped = (
            chunk.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        font = bn_font if mode == "bn" else latin_font
        parts.append(f'<font name="{font}">{escaped}</font>')
        mode = None

    for ch in text:
        is_bn = bool(_BN_CHAR.match(ch))
        # Keep spaces/punctuation with the surrounding script when possible.
        if ch.isspace() or (not is_bn and not ch.isascii()):
            if mode is None:
                mode = "latin"
            buf.append(ch)
            continue
        next_mode = "bn" if is_bn else "latin"
        if mode is None:
            mode = next_mode
        elif mode != next_mode:
            flush()
            mode = next_mode
        buf.append(ch)
    flush()
    return "".join(parts)
