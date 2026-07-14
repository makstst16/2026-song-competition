from pathlib import Path
import math
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parent
BACKGROUND = ROOT / "generated" / "poster-background-b2-musical.png"
QR_IMAGE = ROOT / "assets" / "registration-qr.png"
QR_TRANSPARENT = ROOT / "assets" / "registration-qr-transparent.png"
LOGO_IMAGE = ROOT / "assets" / "organisation-logo.jpg"
OUT_DIR = ROOT / "final"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
MARGIN = 70

FONT_MEDIUM = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_LIGHT = "/System/Library/Fonts/STHeiti Light.ttc"


def font(size, light=False):
    return ImageFont.truetype(FONT_LIGHT if light else FONT_MEDIUM, size=size)


def cover(im, size):
    target_w, target_h = size
    scale = max(target_w / im.width, target_h / im.height)
    resized = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def rounded_panel(base, box, radius, fill, shadow=True, outline=None, width=1):
    x0, y0, x1, y1 = box
    if shadow:
        shadow_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_layer)
        sd.rounded_rectangle((x0, y0 + 8, x1, y1 + 8), radius=radius, fill=(19, 92, 101, 34))
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(18))
        base.alpha_composite(shadow_layer)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    base.alpha_composite(layer)


def dashed_round_rect(draw, box, radius, fill, outline, width=3, dash=12, gap=9):
    draw.rounded_rectangle(box, radius=radius, fill=fill)
    x0, y0, x1, y1 = box
    for x in range(x0 + radius, x1 - radius, dash + gap):
        draw.line((x, y0, min(x + dash, x1 - radius), y0), fill=outline, width=width)
        draw.line((x, y1, min(x + dash, x1 - radius), y1), fill=outline, width=width)
    for y in range(y0 + radius, y1 - radius, dash + gap):
        draw.line((x0, y, x0, min(y + dash, y1 - radius)), fill=outline, width=width)
        draw.line((x1, y, x1, min(y + dash, y1 - radius)), fill=outline, width=width)
    # Clean rounded corners over the dashed square joins.
    draw.arc((x0, y0, x0 + 2 * radius, y0 + 2 * radius), 180, 270, fill=outline, width=width)
    draw.arc((x1 - 2 * radius, y0, x1, y0 + 2 * radius), 270, 360, fill=outline, width=width)
    draw.arc((x0, y1 - 2 * radius, x0 + 2 * radius, y1), 90, 180, fill=outline, width=width)
    draw.arc((x1 - 2 * radius, y1 - 2 * radius, x1, y1), 0, 90, fill=outline, width=width)


def center_text(draw, xy, text, fnt, fill, **kwargs):
    draw.text(xy, text, font=fnt, fill=fill, anchor="mm", **kwargs)


def fit_font(text, max_width, start_size, min_size=24, light=False):
    for size in range(start_size, min_size - 1, -1):
        fnt = font(size, light=light)
        box = fnt.getbbox(text)
        if box[2] - box[0] <= max_width:
            return fnt
    return font(min_size, light=light)


def pill(draw, box, label, fill, text_fill, fnt, outline=None):
    draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=fill, outline=outline, width=2)
    center_text(draw, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 1), label, fnt, text_fill)


def paste_rhythmic_glyph(base, center, character, fnt, fill, angle):
    tile = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.text(
        (110, 112),
        character,
        font=fnt,
        fill=fill,
        anchor="mm",
        stroke_width=1,
        stroke_fill=(255, 255, 255, 105),
    )
    tile = tile.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    base.alpha_composite(tile, (round(center[0] - tile.width / 2), round(center[1] - tile.height / 2)))


def draw_music_note(draw, x, y, scale, color, double=False):
    head_w = round(24 * scale)
    head_h = round(16 * scale)
    stem_h = round(58 * scale)
    stem_w = max(3, round(5 * scale))

    def one_note(nx, ny):
        draw.ellipse((nx - head_w // 2, ny - head_h // 2, nx + head_w // 2, ny + head_h // 2), fill=color)
        draw.line((nx + head_w // 2 - 1, ny, nx + head_w // 2 - 1, ny - stem_h), fill=color, width=stem_w)

    one_note(x, y)
    if double:
        offset = round(34 * scale)
        one_note(x + offset, y - round(8 * scale))
        top_y = y - stem_h
        draw.line((x + head_w // 2 - 1, top_y, x + offset + head_w // 2 - 1, top_y - round(8 * scale)), fill=color, width=stem_w)
        draw.line((x + head_w // 2 - 1, top_y + round(9 * scale), x + offset + head_w // 2 - 1, top_y + round(1 * scale)), fill=color, width=stem_w)
    else:
        sx = x + head_w // 2 - 1
        top_y = y - stem_h
        draw.arc((sx - round(4 * scale), top_y, sx + round(31 * scale), top_y + round(35 * scale)), 265, 75, fill=color, width=stem_w)


def draw_equalizer(draw, x, y, scale, color):
    heights = (25, 48, 34, 62, 39, 54, 28)
    bar_w = max(5, round(7 * scale))
    gap = round(8 * scale)
    for idx, height in enumerate(heights):
        h = round(height * scale)
        bx = round(x + idx * (bar_w + gap))
        draw.rounded_rectangle((bx, round(y - h / 2), bx + bar_w, round(y + h / 2)), radius=max(2, bar_w // 2), fill=color)


def draw_spark(draw, x, y, size, color):
    draw.line((x - size, y, x + size, y), fill=color, width=max(2, size // 5))
    draw.line((x, y - size, x, y + size), fill=color, width=max(2, size // 5))
    diag = round(size * 0.58)
    draw.line((x - diag, y - diag, x + diag, y + diag), fill=color, width=max(1, size // 8))
    draw.line((x - diag, y + diag, x + diag, y - diag), fill=color, width=max(1, size // 8))


def draw_wave_lines(draw, x0, x1, center_y, amplitude, color, count=4):
    for row in range(count):
        points = []
        y_offset = (row - (count - 1) / 2) * 12
        for x in range(x0, x1 + 1, 6):
            phase = (x - x0) / max(1, x1 - x0) * math.pi * 2.15
            points.append((x, center_y + y_offset + math.sin(phase) * amplitude))
        draw.line(points, fill=color, width=3)


def build():
    bg = cover(Image.open(BACKGROUND).convert("RGB"), (W, H)).convert("RGBA")
    # Gentle top veil keeps title contrast high while preserving generated texture.
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    for y in range(0, 720):
        alpha = int(78 * (1 - y / 720))
        vd.line((0, y, W, y), fill=(246, 252, 249, alpha))
    bg.alpha_composite(veil)
    draw = ImageDraw.Draw(bg)

    dark = (18, 86, 97, 255)
    teal = (31, 129, 137, 255)
    mint = (213, 245, 232, 255)
    cream = (255, 251, 235, 255)
    gold = (233, 171, 64, 255)
    white = (255, 255, 255, 255)
    muted = (68, 112, 116, 255)

    # Organiser strip with a reserved logo area immediately beside the church name.
    rounded_panel(bg, (MARGIN, 58, W - MARGIN, 164), 34, (255, 255, 255, 205), shadow=True)
    draw = ImageDraw.Draw(bg)
    if LOGO_IMAGE.exists():
        logo = Image.open(LOGO_IMAGE).convert("RGB")
        diff = ImageChops.difference(logo, Image.new("RGB", logo.size, "white")).convert("L")
        mark = diff.point(lambda value: 255 if value > 18 else 0)
        bbox = mark.getbbox()
        if bbox:
            pad = 24
            bbox = (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(logo.width, bbox[2] + pad),
                min(logo.height, bbox[3] + pad),
            )
            logo = logo.crop(bbox)
        logo.thumbnail((88, 88), Image.Resampling.LANCZOS)
        logo_x = 123 - logo.width // 2
        logo_y = 111 - logo.height // 2
        bg.paste(logo, (logo_x, logo_y))
    else:
        dashed_round_rect(draw, (88, 76, 158, 146), 18, (244, 252, 249, 240), (48, 142, 146, 210), width=2, dash=8, gap=6)
        center_text(draw, (123, 103), "機構", font(16), teal)
        center_text(draw, (123, 124), "LOGO", font(14), muted)
    draw.text((181, 111), "中華傳道會基石堂", font=font(42), fill=dark, anchor="lm")

    pill(draw, (MARGIN, 202, W - MARGIN, 266), "2026  詩歌創作及演繹比賽", (19, 113, 122, 238), white, font(27))

    # Main title: staggered glyphs and alternating weight/colour create a musical rhythm.
    title_chars = (
        ("神", (222, 354), 124, -4, dark),
        ("蹟", (348, 376), 118, 3, teal),
        ("經", (592, 352), 124, -2, dark),
        ("歷", (716, 374), 116, 3, teal),
        ("神", (840, 354), 124, -3, dark),
    )
    for character, position, size, angle, colour in title_chars:
        paste_rhythmic_glyph(bg, position, character, font(size), colour, angle)
    cross_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    cross_draw = ImageDraw.Draw(cross_layer)
    cross_draw.rounded_rectangle((474, 335, 486, 395), radius=6, fill=gold)
    cross_draw.rounded_rectangle((456, 351, 504, 365), radius=7, fill=gold)
    cross_glow = cross_layer.filter(ImageFilter.GaussianBlur(8))
    cross_glow.putalpha(cross_glow.getchannel("A").point(lambda value: round(value * 0.45)))
    bg.alpha_composite(cross_glow)
    bg.alpha_composite(cross_layer)
    draw = ImageDraw.Draw(bg)
    center_text(draw, (W / 2, 457), "MIRACLE  ·  EXPERIENCE GOD", font(21), teal)
    draw.rounded_rectangle((370, 492, 710, 498), radius=3, fill=gold)
    center_text(draw, (W / 2, 552), "用音樂記低恩典   用歌聲見證神蹟", font(38), dark)

    # Entry formats.
    chip_y = 624
    gap = 14
    chip_w = (W - 2 * MARGIN - 2 * gap) // 3
    for i, label in enumerate(("原創歌曲", "舊曲新詞", "重新演繹詩歌")):
        x0 = MARGIN + i * (chip_w + gap)
        pill(draw, (x0, chip_y, x0 + chip_w, chip_y + 62), label, (255, 255, 255, 214), dark, fit_font(label, chip_w - 32, 25, 20), outline=(131, 197, 193, 210))

    # Timeline card.
    rounded_panel(bg, (MARGIN, 734, W - MARGIN, 1258), 42, (255, 255, 255, 218), shadow=True, outline=(255, 255, 255, 170), width=2)
    draw = ImageDraw.Draw(bg)

    # Low-contrast music stickers fill the open right side without competing with dates.
    timeline_deco = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(timeline_deco)
    td.ellipse((810, 842, 930, 962), fill=(221, 241, 255, 128), outline=(255, 255, 255, 225), width=7)
    draw_music_note(td, 857, 923, 1.0, (36, 115, 177, 170), double=True)
    td.rounded_rectangle((842, 1027, 962, 1127), radius=28, fill=(255, 224, 219, 118), outline=(255, 255, 255, 220), width=7)
    draw_equalizer(td, 863, 1077, 0.72, (197, 96, 119, 145))
    td.arc((792, 1095, 982, 1275), 195, 342, fill=(31, 129, 137, 44), width=5)
    td.arc((816, 1119, 958, 1251), 195, 342, fill=(31, 129, 137, 36), width=4)
    draw_spark(td, 924, 974, 14, (233, 171, 64, 130))
    draw_spark(td, 790, 1166, 10, (31, 129, 137, 95))
    bg.alpha_composite(timeline_deco)
    draw = ImageDraw.Draw(bg)
    draw.text((110, 778), "重要日程", font=font(34), fill=dark)
    draw.text((W - 110, 792), "KEY DATES", font=font(15, light=True), fill=teal, anchor="ra")

    timeline_x = 152
    draw.line((timeline_x, 866, timeline_x, 1162), fill=(75, 163, 163, 160), width=4)
    events = [
        (886, "2026年7月－11月", "收集作品"),
        (1008, "2026年12月－2027年1月中", "全民投票，選出優秀作品"),
        (1130, "2027年1月31日", "感恩音樂會｜得獎作品演繹及分享"),
    ]
    for idx, (y, date, desc) in enumerate(events):
        dot_fill = gold if idx == 2 else teal
        draw.ellipse((timeline_x - 15, y - 15, timeline_x + 15, y + 15), fill=white, outline=dot_fill, width=7)
        date_font = fit_font(date, 570, 35, min_size=27)
        draw.text((205, y - 31), date, font=date_font, fill=dark)
        desc_font = fit_font(desc, 720, 29, min_size=23, light=True)
        draw.text((205, y + 17), desc, font=desc_font, fill=muted)

    # Prize / concert highlight.
    rounded_panel(bg, (MARGIN, 1302, W - MARGIN, 1494), 38, (17, 103, 113, 235), shadow=True)
    draw = ImageDraw.Draw(bg)

    prize_deco = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(prize_deco)
    draw_wave_lines(pd, 755, 960, 1364, 16, (220, 247, 239, 48), count=4)
    draw_music_note(pd, 886, 1380, 0.72, (244, 190, 79, 145), double=True)
    draw_spark(pd, 948, 1340, 13, (255, 255, 255, 115))
    draw_spark(pd, 810, 1398, 8, (244, 190, 79, 105))
    bg.alpha_composite(prize_deco)
    draw = ImageDraw.Draw(bg)
    pill(draw, (102, 1334, 292, 1385), "得獎作品", (244, 190, 79, 255), dark, font(24))
    draw.text((110, 1412), "設有獎品，更會登上感恩音樂會舞台", font=fit_font("設有獎品，更會登上感恩音樂會舞台", 800, 38, 30), fill=white)
    draw.text((W - 110, 1462), "2027 年 1 月 31 日  ·  現場演繹與分享", font=font(24, light=True), fill=(220, 247, 239, 255), anchor="ra")

    # CTA and QR placeholder.
    rounded_panel(bg, (MARGIN, 1542, W - MARGIN, 1848), 42, (255, 255, 255, 225), shadow=True)
    draw = ImageDraw.Draw(bg)

    cta_deco = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(cta_deco)
    cd.ellipse((602, 1687, 714, 1799), fill=(220, 247, 239, 102), outline=(255, 255, 255, 205), width=7)
    cd.arc((622, 1707, 694, 1779), 198, 342, fill=(31, 129, 137, 105), width=5)
    cd.arc((636, 1721, 680, 1765), 198, 342, fill=(31, 129, 137, 78), width=4)
    draw_music_note(cd, 653, 1757, 0.55, (31, 129, 137, 125), double=False)
    draw_spark(cd, 706, 1666, 10, (233, 171, 64, 120))
    bg.alpha_composite(cta_deco)
    draw = ImageDraw.Draw(bg)
    draw.text((112, 1592), "讓你的歌聲，成為見證。", font=font(38), fill=dark)
    draw.text((112, 1650), "掃描 QR Code 報名及提交作品", font=font(26, light=True), fill=muted)
    draw.text((112, 1717), "作品徵集｜2026 年 7 月至 11 月", font=font(25), fill=teal)
    draw.text((112, 1763), "詳情及參賽細則將於報名頁公布", font=font(21, light=True), fill=muted)

    qr_box = (758, 1583, 1008, 1833)
    if QR_IMAGE.exists():
        draw.rounded_rectangle(qr_box, radius=28, outline=(255, 255, 255, 255), width=7)
        qr_source = Image.open(QR_IMAGE).convert("RGB")
        source_diff = ImageChops.difference(qr_source, Image.new("RGB", qr_source.size, "white")).convert("L")
        source_alpha = source_diff.point(lambda value: 0 if value < 6 else min(255, (value - 6) * 12))
        qr_source_rgba = qr_source.convert("RGBA")
        qr_source_rgba.putalpha(source_alpha)
        qr_source_rgba.save(QR_TRANSPARENT)

        qr_rgb = qr_source.resize((226, 226), Image.Resampling.LANCZOS)
        white_diff = ImageChops.difference(qr_rgb, Image.new("RGB", qr_rgb.size, "white")).convert("L")
        qr_alpha = white_diff.point(lambda value: 0 if value < 6 else min(255, (value - 6) * 12))
        qr = qr_rgb.convert("RGBA")
        qr.putalpha(qr_alpha)
        bg.alpha_composite(qr, (770, 1595))
    else:
        dashed_round_rect(draw, qr_box, 28, (244, 252, 249, 245), (31, 129, 137, 230), width=4, dash=14, gap=10)
        center_text(draw, (883, 1688), "報名", font(30), dark)
        center_text(draw, (883, 1730), "QR CODE", font(20), teal)
        center_text(draw, (883, 1772), "稍後加入", font(17, light=True), muted)

    # Footer safe-zone note, deliberately subtle and easy to remove later.
    final = bg.convert("RGB")
    final.save(OUT_DIR / "miracle-experience-god-poster-9x16.png", quality=96, dpi=(300, 300))
    final.resize((540, 960), Image.Resampling.LANCZOS).save(OUT_DIR / "miracle-experience-god-poster-preview.png", quality=92)


if __name__ == "__main__":
    build()
