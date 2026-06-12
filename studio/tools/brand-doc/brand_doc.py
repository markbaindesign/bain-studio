"""
brand_doc.py — Bain Design branded document generator
======================================================
Converts a Markdown file to a branded PDF using Bain Design identity.

Usage:
    python3 brand_doc.py input.md [output.pdf]

Requirements:
    pip install reportlab pillow markdown
"""

import sys, os, re, argparse
from pathlib import Path
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ─── Paths ───────────────────────────────────────────────────────────────────

BASE   = Path(__file__).parent
FONTS  = BASE / 'assets/fonts'
IMAGES = BASE / 'assets/images'

FONT_FILES = {
    'JetBrainsMono-Regular': FONTS / 'JetBrainsMono-Regular.ttf',
    'JetBrainsMono-Medium':  FONTS / 'JetBrainsMono-Medium.ttf',
    'JetBrainsMono-Bold':    FONTS / 'JetBrainsMono-Bold.ttf',
    'IBMPlexMono-Regular':   FONTS / 'IBMPlexMono-Regular.ttf',
}

MARK = IMAGES / 'bain-logo.png'

# ─── Brand tokens ─────────────────────────────────────────────────────────────

PAPER      = HexColor('#E8DFCC')
PAPER_DEEP = HexColor('#DDD2BB')
INK        = HexColor('#141413')
GRAPHITE   = HexColor('#3D3D3A')
PENCIL     = HexColor('#8C8A85')
RULE       = HexColor('#1F1F1D')
RULE_SOFT  = HexColor('#D8D0C0')
CLAY       = HexColor('#C96442')
CLAY_HEX   = 'C96442'

W, H = A4


# ─── Font registration ────────────────────────────────────────────────────────

def register_fonts():
    F = {}
    for logical, key, fallback in [
        ('Mono',       'JetBrainsMono-Regular', 'Courier'),
        ('MonoMedium', 'JetBrainsMono-Medium',  'Courier'),
        ('MonoBold',   'JetBrainsMono-Bold',     'Courier-Bold'),
        ('Code',       'IBMPlexMono-Regular',    'Courier'),
    ]:
        path = FONT_FILES.get(key)
        if path and path.exists():
            try:
                pdfmetrics.registerFont(TTFont(logical, str(path)))
                F[logical] = logical
                print(f'  ✓ {logical}')
            except Exception as e:
                print(f'  ✗ {logical} ({e}) → {fallback}')
                F[logical] = fallback
        else:
            print(f'  – {logical} → {fallback}')
            F[logical] = fallback
    return F


# ─── Styles ───────────────────────────────────────────────────────────────────

def build_styles(F):
    s = getSampleStyleSheet()
    def add(name, **kw):
        s.add(ParagraphStyle(name=name, **kw))

    add('BH1', fontName=F['MonoBold'],   fontSize=22, textColor=INK,      spaceBefore=10, spaceAfter=6,  leading=26)
    add('BH2', fontName=F['MonoBold'],   fontSize=16, textColor=INK,      spaceBefore=10, spaceAfter=5,  leading=20)
    add('BH3', fontName=F['MonoBold'],   fontSize=13, textColor=CLAY,     spaceBefore=8,  spaceAfter=4,  leading=17)
    add('BH4', fontName=F['MonoMedium'], fontSize=11, textColor=INK,      spaceBefore=6,  spaceAfter=3,  leading=15)
    add('BH5', fontName=F['MonoMedium'], fontSize=10, textColor=GRAPHITE, spaceBefore=5,  spaceAfter=2,  leading=14)
    add('BH6', fontName=F['MonoMedium'], fontSize=9,  textColor=PENCIL,   spaceBefore=4,  spaceAfter=2,  leading=13)

    add('BBody',     fontName=F['Mono'],       fontSize=10, textColor=INK,     spaceAfter=6,  leading=17)
    add('BListItem', fontName=F['Mono'],       fontSize=10, textColor=INK,     spaceAfter=3,  leading=16, leftIndent=14)
    add('BQuote',    fontName=F['Mono'],       fontSize=10, textColor=GRAPHITE, spaceBefore=4, spaceAfter=4, leading=17, leftIndent=12)
    add('BCaption',  fontName=F['Code'],       fontSize=8,  textColor=PENCIL,  spaceAfter=3,  leading=11)
    add('BTableHead',fontName=F['MonoBold'],   fontSize=9,  textColor=INK,     spaceAfter=0,  leading=13)
    add('BTableCell',fontName=F['Mono'],       fontSize=9,  textColor=INK,     spaceAfter=0,  leading=13)
    return s


# ─── Custom flowables ─────────────────────────────────────────────────────────

class HRule(Flowable):
    def __init__(self, color=None, thickness=0.5, space=3):
        super().__init__()
        self.color     = color or RULE_SOFT
        self.thickness = thickness
        self.space     = space

    def wrap(self, aw, ah):
        self.width = aw
        return aw, self.thickness + self.space * 2

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.space, self.width, self.space)


class CodeBlock(Flowable):
    def __init__(self, text, font_name, font_size=9):
        super().__init__()
        self._text      = text
        self._font_name = font_name
        self._font_size = font_size
        self._pad       = 10

    def wrap(self, aw, ah):
        self.width  = aw
        lines       = self._text.split('\n')
        line_h      = self._font_size * 1.5
        self.height = len(lines) * line_h + self._pad * 2
        return aw, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(INK)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(CLAY)
        c.rect(0, 0, 2.5, self.height, fill=1, stroke=0)
        c.setFillColor(PAPER)
        c.setFont(self._font_name, self._font_size)
        line_h = self._font_size * 1.5
        y = self.height - self._pad - self._font_size
        for line in self._text.split('\n'):
            c.drawString(self._pad + 5, y, line)
            y -= line_h


# ─── Slug helper (GitHub-flavoured anchor convention) ─────────────────────────

def _slug(heading_text):
    """Convert a heading string to a GitHub-style anchor slug."""
    s = heading_text.lower()
    s = re.sub(r'[^\w\s-]', '', s)   # strip punctuation (keep spaces, hyphens, word chars)
    s = re.sub(r'_', '-', s)           # underscores → hyphens
    s = re.sub(r' ', '-', s)           # each space → hyphen (no collapsing, matches GitHub)
    s = s.strip('-')
    return s


# ─── Inline markdown → ReportLab XML ─────────────────────────────────────────

def _inline(text, F):
    # Escape XML special chars first
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # Internal anchor links [label](#anchor) → clickable link
    text = re.sub(
        r'\[([^\]]+)\]\(#([^)]+)\)',
        lambda m: f'<a href="#{m.group(2)}" color="#{CLAY_HEX}">{m.group(1)}</a>',
        text,
    )
    # External links [label](url) → coloured clickable link
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^)]+)\)',
        lambda m: f'<a href="{m.group(2)}" color="#{CLAY_HEX}">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: f'<font name="{F["MonoBold"]}">{m.group(1)}</font>', text)
    text = re.sub(r'__(.+?)__',     lambda m: f'<font name="{F["MonoBold"]}">{m.group(1)}</font>', text)
    text = re.sub(r'\*(.+?)\*',     lambda m: f'<font name="{F["MonoMedium"]}">{m.group(1)}</font>', text)
    text = re.sub(r'_(.+?)_',       lambda m: f'<font name="{F["MonoMedium"]}">{m.group(1)}</font>', text)
    text = re.sub(r'`(.+?)`',       lambda m: '<font name="' + F['Code'] + '" color="#' + CLAY_HEX + '">' + m.group(1) + '</font>', text)
    return text


# ─── Markdown → story ─────────────────────────────────────────────────────────

def md_to_story(md_text, ST, F, skip_h1=False, base_dir=None):
    story = []
    lines = md_text.split('\n')
    TW = W - 36 * mm
    i  = 0

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            story.append(Spacer(1, 3 * mm))
            story.append(CodeBlock('\n'.join(code_lines), F['Code']))
            story.append(Spacer(1, 4 * mm))
            i += 1
            continue

        # HR
        if re.match(r'^[-*_]{3,}\s*$', line):
            story.append(Spacer(1, 2 * mm))
            story.append(HRule(color=RULE, thickness=1))
            story.append(Spacer(1, 2 * mm))
            i += 1
            continue

        # Heading
        hm = re.match(r'^(#{1,6})\s+(.*)', line)
        if hm and skip_h1 and len(hm.group(1)) == 1:
            i += 1
            continue
        if hm:
            level = len(hm.group(1))
            raw_heading = hm.group(2)
            anchor = _slug(raw_heading)
            text  = f'<a name="{anchor}"/>' + _inline(raw_heading, F)
            smap  = {1:'BH1', 2:'BH2', 3:'BH3', 4:'BH4', 5:'BH5', 6:'BH6'}
            if level == 1:
                story.append(Spacer(1, 4 * mm))
                story.append(HRule(color=CLAY, thickness=1.5))
                story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(text, ST[smap.get(level, 'BH6')]))
            if level == 1:
                story.append(HRule(color=RULE_SOFT, thickness=0.5))
            i += 1
            continue

        # Blockquote
        if line.startswith('> '):
            bq_lines = []
            while i < len(lines) and lines[i].startswith('> '):
                bq_lines.append(lines[i][2:])
                i += 1
            bq_text = _inline(' '.join(bq_lines), F)
            bq = Table(
                [[None, Paragraph(bq_text, ST['BQuote'])]],
                colWidths=[3.5, TW - 3.5],
            )
            bq.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), PAPER_DEEP),
                ('BACKGROUND',    (0,0), (0,-1),  CLAY),
                ('LEFTPADDING',   (0,0), (-1,-1), 0),
                ('RIGHTPADDING',  (0,0), (-1,-1), 10),
                ('TOPPADDING',    (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('VALIGN',        (0,0), (-1,-1), 'TOP'),
            ]))
            story.append(Spacer(1, 2 * mm))
            story.append(bq)
            story.append(Spacer(1, 2 * mm))
            continue

        # Unordered list
        if re.match(r'^[-*+]\s+', line):
            while i < len(lines) and re.match(r'^[-*+]\s+', lines[i]):
                text = _inline(re.sub(r'^[-*+]\s+', '', lines[i]), F)
                story.append(Paragraph(
                    f'<font color="#{CLAY_HEX}">–</font>  {text}',
                    ST['BListItem']))
                i += 1
            story.append(Spacer(1, 2 * mm))
            continue

        # Ordered list
        if re.match(r'^\d+\.\s+', line):
            n = 1
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i]):
                text = _inline(re.sub(r'^\d+\.\s+', '', lines[i]), F)
                story.append(Paragraph(
                    '<font color="#' + CLAY_HEX + '" name="' + F['Code'] + '">' + str(n) + '.</font>  ' + text,
                    ST['BListItem']))
                i += 1
                n += 1
            story.append(Spacer(1, 2 * mm))
            continue

        # Table
        if '|' in line and i + 1 < len(lines) and re.match(r'^[\s|:-]+$', lines[i+1]):
            table_lines = []
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i])
                i += 1
            rows = []
            for ti, tl in enumerate(table_lines):
                if re.match(r'^[\s|:-]+$', tl):
                    continue
                cells = [c.strip() for c in tl.strip('|').split('|')]
                style = ST['BTableHead'] if ti == 0 else ST['BTableCell']
                rows.append([Paragraph(_inline(c, F), style) for c in cells])
            if rows:
                col_w = TW / max(len(r) for r in rows)
                t = Table(rows, colWidths=[col_w] * max(len(r) for r in rows), hAlign='LEFT')
                t.setStyle(TableStyle([
                    ('BACKGROUND',    (0,0), (-1,0),  PAPER_DEEP),
                    ('LINEBELOW',     (0,0), (-1,0),  0.8, RULE),
                    ('LINEBELOW',     (0,1), (-1,-1), 0.3, RULE_SOFT),
                    ('TOPPADDING',    (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ('LEFTPADDING',   (0,0), (-1,-1), 6),
                    ('VALIGN',        (0,0), (-1,-1), 'TOP'),
                ]))
                story.append(Spacer(1, 2 * mm))
                story.append(t)
                story.append(Spacer(1, 3 * mm))
            continue

        # Page break directive
        if line.strip().lower() in ('---pagebreak---', '<!-- pagebreak -->'):
            story.append(PageBreak())
            i += 1
            continue

        # Image
        im = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', line)
        if im:
            img_path = Path(im.group(2))
            if not img_path.is_absolute() and base_dir:
                img_path = base_dir / img_path
            if img_path.exists():
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(img_path) as pil_img:
                        iw, ih = pil_img.size
                    max_w = TW
                    scale = min(max_w / iw, 60 * mm / ih, 1.0)
                    story.append(Spacer(1, 3 * mm))
                    story.append(RLImage(str(img_path), width=iw * scale, height=ih * scale))
                    story.append(Spacer(1, 3 * mm))
                except Exception as e:
                    story.append(Paragraph(f'[image: {img_path.name}]', ST['BCaption']))
            else:
                story.append(Paragraph(f'[image not found: {img_path.name}]', ST['BCaption']))
            i += 1
            continue

        # Body paragraph
        if line.strip():
            story.append(Paragraph(_inline(line, F), ST['BBody']))
        elif story and not isinstance(story[-1], Spacer):
            story.append(Spacer(1, 2 * mm))

        i += 1

    return story


# ─── Page callbacks ───────────────────────────────────────────────────────────

def _cover(canvas, doc, title, subtitle, F):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFillColor(CLAY)
    canvas.rect(0, 0, 3.5 * mm, H, fill=1, stroke=0)

    # Draw the Bd mark: ink square with paper "Bd" text
    mk = 14 * mm
    mx = W - mk - 16 * mm
    my = H - mk - 15 * mm
    canvas.setFillColor(INK)
    canvas.rect(mx, my, mk, mk, fill=1, stroke=0)
    canvas.setFillColor(PAPER)
    canvas.setFont(F['MonoBold'], mk * 0.52)
    canvas.drawCentredString(mx + mk / 2, my + mk * 0.22, 'Bd')

    canvas.setFillColor(INK)
    canvas.setFont(F['MonoBold'], 30)
    words = title.split()
    line, title_lines = '', []
    for w in words:
        test = (line + ' ' + w).strip()
        if canvas.stringWidth(test, F['MonoBold'], 30) < W - 48 * mm:
            line = test
        else:
            title_lines.append(line)
            line = w
    if line:
        title_lines.append(line)

    ty = H * 0.50 + (len(title_lines) - 1) * 16
    for tl in title_lines:
        canvas.drawString(18 * mm, ty, tl)
        ty -= 36

    if subtitle:
        canvas.setFont(F['Mono'], 10)
        canvas.setFillColor(GRAPHITE)
        canvas.drawString(18 * mm, ty - 4, subtitle)
        ty -= 18

    canvas.setStrokeColor(CLAY)
    canvas.setLineWidth(1.5)
    canvas.line(18 * mm, ty - 10, 18 * mm + 36 * mm, ty - 10)

    canvas.setFont(F['Code'], 8)
    canvas.setFillColor(PENCIL)
    today = date.today().strftime('%B %Y')
    canvas.drawString(18 * mm, 14 * mm, f'Bain Design  ·  mark@bain.design  ·  {today}')
    canvas.restoreState()


def _header_footer(canvas, doc, title, F):
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setStrokeColor(RULE_SOFT)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, H - 13 * mm, W - 18 * mm, H - 13 * mm)
    canvas.setFont(F['Code'], 8)
    canvas.setFillColor(PENCIL)
    canvas.drawString(18 * mm, H - 11 * mm, title)
    canvas.drawRightString(W - 18 * mm, H - 11 * mm, str(doc.page))
    canvas.line(18 * mm, 12 * mm, W - 18 * mm, 12 * mm)
    canvas.setFont(F['Code'], 7)
    canvas.drawString(18 * mm, 9 * mm, 'Bain Design  ·  mark@bain.design')
    canvas.restoreState()


def _one_pager_header(canvas, doc, title, F):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    # Title
    canvas.setFillColor(INK)
    canvas.setFont(F['MonoBold'], 14)
    title_y = H - 14 * mm
    canvas.drawString(14 * mm, title_y, title)

    # Bd mark — vertically centred with title text
    mk = 9 * mm
    mx = W - mk - 14 * mm
    my = title_y - mk * 0.18
    canvas.setFillColor(INK)
    canvas.rect(mx, my, mk, mk, fill=1, stroke=0)
    canvas.setFillColor(PAPER)
    canvas.setFont(F['MonoBold'], mk * 0.52)
    canvas.drawCentredString(mx + mk / 2, my + mk * 0.22, 'Bd')

    # Rule below header
    canvas.setStrokeColor(CLAY)
    canvas.setLineWidth(1)
    canvas.line(14 * mm, H - 19 * mm, W - 14 * mm, H - 19 * mm)

    # Footer
    canvas.setStrokeColor(RULE_SOFT)
    canvas.setLineWidth(0.5)
    canvas.line(14 * mm, 12 * mm, W - 14 * mm, 12 * mm)
    canvas.setFont(F['Code'], 7)
    canvas.setFillColor(PENCIL)
    today = date.today().strftime('%B %Y')
    canvas.drawString(14 * mm, 9 * mm, f'Bain Design  ·  mark@bain.design  ·  {today}')
    canvas.restoreState()


# ─── Build ────────────────────────────────────────────────────────────────────

def build(input_path, output_path=None, one_pager=False):
    input_path = Path(input_path)
    if not input_path.exists():
        print(f'Error: {input_path} not found', file=sys.stderr)
        sys.exit(1)

    if output_path is None:
        output_path = input_path.with_suffix('.pdf')
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    md_text = input_path.read_text(encoding='utf-8')

    title_match = re.match(r'^#\s+(.+)', md_text, re.MULTILINE)
    title = (title_match.group(1) if title_match
             else input_path.stem.replace('-', ' ').replace('_', ' ').title())

    subtitle = ''
    for ln in md_text.split('\n')[1:6]:
        if ln.startswith('> '):
            subtitle = ln[2:].strip()
            break

    print(f'Input:  {input_path}')
    print(f'Output: {output_path}')
    F  = register_fonts()
    ST = build_styles(F)

    if one_pager:
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=14 * mm, rightMargin=14 * mm,
            topMargin=24 * mm,  bottomMargin=16 * mm,
            title=title, author='Bain Design',
        )
        story = md_to_story(md_text, ST, F, skip_h1=True, base_dir=input_path.parent)
        hf = lambda c, d: _one_pager_header(c, d, title, F)
        doc.build(story, onFirstPage=hf, onLaterPages=hf)
    else:
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=20 * mm,  bottomMargin=18 * mm,
            title=title, author='Bain Design',
        )
        story = [Spacer(1, 720)]   # fill cover page
        story.extend(md_to_story(md_text, ST, F, base_dir=input_path.parent))
        doc.build(
            story,
            onFirstPage=lambda c, d: _cover(c, d, title, subtitle, F),
            onLaterPages=lambda c, d: _header_footer(c, d, title, F),
        )
    print(f'\nDone → {output_path}')
    return output_path


def main():
    p = argparse.ArgumentParser(description='Convert Markdown to Bain Design branded PDF')
    p.add_argument('input',  help='Input .md file')
    p.add_argument('output', nargs='?', help='Output .pdf path (optional)')
    p.add_argument('--one-pager', action='store_true', help='No cover page; branded header with title')
    args = p.parse_args()
    build(args.input, args.output, one_pager=args.one_pager)


if __name__ == '__main__':
    main()
