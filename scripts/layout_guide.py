"""세로 현수막(600x1800mm) 구조 레이아웃 가이드.

  python scripts/layout_guide.py
  → output/layout_wireframe.png   구역 설계도 (mm 표기)
  → output/layout_overlay.png     키비주얼 위에 구역 겹쳐 보기
  → output/layout_guide.png       투명 가이드 레이어 (Canva·미리캔버스에 겹쳐 쓰기용)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
FONT_DIR = OUT / "cache"   # fonts/*.woff2 → otf 변환본 (PIL은 woff2를 못 읽음)

W_MM, H_MM = 600, 1800
PX = 2                      # 1mm = 2px
SIDE = 40                   # 좌우 여백(mm)

# (이름, 시작mm, 끝mm, 설명, 글자 높이, 색)
ZONES = [
    ("상단 여백", 0, 70, "봉·아일렛 마감 — 글자 금지", "", (200, 80, 80)),
    ("브랜드", 90, 150, "IDeL 로고", "로고 높이 약 50mm", (90, 90, 90)),
    ("헤드라인", 230, 530, "메인 문구 2줄", "글자 90–120mm · Bold", (30, 110, 200)),
    ("서브 문구", 550, 630, "한 줄 설명", "글자 40–50mm · Medium", (30, 150, 170)),
    ("숨 쉬는 여백", 630, 900, "빈 벽 — 문구와 화분 사이 간격 (레퍼런스처럼 비워 둠)", "", (150, 150, 150)),
    ("이미지", 900, 1400, "합성 키비주얼 (화분 + 그림자)", "글자 없음", (70, 150, 70)),
    ("특징", 1450, 1620, "3칸: 받침 발 · 다공 배수 · 골 구조", "글자 35–40mm", (200, 130, 30)),
    ("하단 정보", 1640, 1730, "제품명 · 연락처 · QR", "글자 25–30mm", (130, 80, 170)),
    ("하단 여백", 1730, 1800, "봉 마감 — 글자 금지", "", (200, 80, 80)),
]


def font(weight, size):
    return ImageFont.truetype(str(FONT_DIR / f"Pretendard-{weight}.otf"), size)


def ensure_fonts():
    for w in ("Bold", "Medium", "Regular"):
        dst = FONT_DIR / f"Pretendard-{w}.otf"
        if not dst.exists():
            from fontTools.ttLib import TTFont
            FONT_DIR.mkdir(parents=True, exist_ok=True)
            f = TTFont(ROOT / "fonts" / f"Pretendard-{w}.woff2")
            f.flavor = None
            f.save(dst)


def dashed_rect(d, box, color, width=3, dash=14):
    x0, y0, x1, y1 = box
    for x in range(x0, x1, dash * 2):
        d.line([(x, y0), (min(x + dash, x1), y0)], fill=color, width=width)
        d.line([(x, y1), (min(x + dash, x1), y1)], fill=color, width=width)
    for y in range(y0, y1, dash * 2):
        d.line([(x0, y), (x0, min(y + dash, y1))], fill=color, width=width)
        d.line([(x1, y), (x1, min(y + dash, y1))], fill=color, width=width)


def draw_zones(img, labels=True, fill_alpha=40):
    W, H = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for name, a, b, desc, size, col in ZONES:
        margin = name.endswith("여백")
        x0, x1 = (0, W - 1) if margin else (SIDE * PX, W - 1 - SIDE * PX)
        box = (x0, a * PX, x1, b * PX)
        breathing = name == "숨 쉬는 여백"
        if not breathing:
            d.rectangle(box, fill=col + (fill_alpha if not margin else fill_alpha + 20,))
            dashed_rect(d, box, col + (255,))
        if labels:
            cx = W // 2
            top = a * PX + (b - a) * PX // 2
            if name == "이미지":                 # 화분을 가리지 않게 구역 위쪽에 표기
                top = a * PX + 60
            lines = [(name, font("Bold", 34)), (desc, font("Medium", 24))]
            if size:
                lines.append((size, font("Regular", 22)))
            total = sum(f.size + 8 for _, f in lines)
            y = top - total // 2
            for text, f in lines:
                d.text((cx, y), text, font=f, fill=col + (255,), anchor="ma")
                y += f.size + 8
    return Image.alpha_composite(img.convert("RGBA"), layer)


def draw_dimensions(img):
    """오른쪽 바깥에 mm 눈금."""
    W, H = img.size
    pad = 150
    out = Image.new("RGBA", (W + pad, H), (255, 255, 255, 255))
    out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    f = font("Medium", 20)
    marks = sorted({v for _, a, b, *_ in ZONES for v in (a, b)})
    for mm in marks:
        y = min(H - 1, mm * PX)
        d.line([(W, y), (W + 22, y)], fill=(60, 60, 60, 255), width=2)
        d.text((W + 28, y), f"{mm}", font=f, fill=(60, 60, 60, 255), anchor="lm")
    # 좌우 여백 표시
    for x in (SIDE * PX, W - SIDE * PX):
        for y in range(0, H, 24):
            d.line([(x, y), (x, y + 10)], fill=(200, 80, 80, 160), width=1)
    d.text((W + 28, 18), "mm", font=font("Bold", 20), fill=(60, 60, 60, 255), anchor="lm")
    return out


def title_bar(img, text):
    bar = 90
    out = Image.new("RGBA", (img.width, img.height + bar), (255, 255, 255, 255))
    out.paste(img, (0, bar))
    d = ImageDraw.Draw(out)
    d.text((24, bar // 2), text, font=font("Bold", 30), fill=(30, 30, 30, 255), anchor="lm")
    return out


def main():
    ensure_fonts()
    W, H = W_MM * PX, H_MM * PX

    base = Image.new("RGBA", (W, H), (246, 246, 247, 255))
    wire = title_bar(draw_dimensions(draw_zones(base)), "세로 현수막 600×1800mm — 구조 레이아웃")
    wire.convert("RGB").save(OUT / "layout_wireframe.png")

    kv = Image.open(OUT / "idel_keyvisual_full.jpg").convert("RGB").resize((W, H), Image.LANCZOS)
    over = title_bar(draw_dimensions(draw_zones(kv, fill_alpha=55)), "키비주얼 + 구조 레이아웃")
    over.convert("RGB").save(OUT / "layout_overlay.png")

    guide = draw_zones(Image.new("RGBA", (W, H), (0, 0, 0, 0)), labels=True, fill_alpha=25)
    guide.save(OUT / "layout_guide.png")

    sheet = Image.new("RGB", (wire.width + over.width + 60, max(wire.height, over.height)), "white")
    sheet.paste(wire.convert("RGB"), (0, 0))
    sheet.paste(over.convert("RGB"), (wire.width + 60, 0))
    sheet.save(OUT / "layout_sheet.jpg", quality=92)
    print("saved layout_wireframe.png, layout_overlay.png, layout_guide.png, layout_sheet.jpg")


if __name__ == "__main__":
    main()
