"""설명형 세로 배너(600x1800mm) 레이아웃 예시.

  python scripts/info_banner_mockup.py  → output/info_banner_mockup.jpg

실제 소스(assets/)를 사용하고, 아직 없는 자료(지게차 테스트 사진, QR, 규격)는 자리 표시만 한다.
로고는 시안(draft_v4) 미리보기에서 잘라 쓰므로 해상도가 낮다 — 레이아웃 확인용.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
POTS = A / "IDeL 화분 사진"
OUT = ROOT / "output"
FONT = OUT / "cache" / "Pretendard-{}.otf"   # layout_guide.py가 woff2 → otf 변환

MM = 2                      # 1mm = 2px
W, H = 600 * MM, 1800 * MM
L, R = 40 * MM, 560 * MM    # 좌우 여백 40mm

BG_TOP, BG_BOTTOM = (214, 218, 223), (236, 237, 239)
INK, SUB, LINE = (30, 32, 35), (95, 100, 106), (190, 194, 199)
GREEN, RED = (0, 146, 70), (206, 43, 55)
PANEL = (30, 32, 35)


def mm(v):
    return int(round(v * MM))


def font(weight, glyph_mm):
    """한글 글자 높이(mm) 기준 크기."""
    return ImageFont.truetype(str(FONT).format(weight), int(glyph_mm * MM / 0.78))


def fit(im, box_w, box_h):
    im = im.copy()
    im.thumbnail((box_w, box_h), Image.LANCZOS)
    return im


def cover(im, box_w, box_h):
    return ImageOps.fit(im, (box_w, box_h), Image.LANCZOS, centering=(0.5, 0.55))


def placeholder(d, box, label):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(70, 74, 80))
    for x in range(x0 - (y1 - y0), x1, 26):
        d.line([(max(x0, x), y0 + max(0, x0 - x)), (min(x1, x + (y1 - y0)), min(y1, y0 + (x1 - x)))], fill=(82, 86, 92), width=6)
    d.text(((x0 + x1) // 2, (y0 + y1) // 2), label, font=font("Bold", 13), fill=(200, 204, 210), anchor="mm")


def paste_rgba(canvas, im, xy):
    im = im.convert("RGBA")
    canvas.alpha_composite(im, (int(xy[0]), int(xy[1])))


def main():
    canvas = Image.new("RGBA", (W, H))
    grad = np.linspace(0, 1, H)[:, None, None]
    bg = np.array(BG_TOP) * (1 - grad) + np.array(BG_BOTTOM) * grad
    canvas.paste(Image.fromarray(np.broadcast_to(bg, (H, W, 3)).astype(np.uint8)).convert("RGBA"))
    d = ImageDraw.Draw(canvas)
    cx = W // 2

    draft = Image.open(A / "drafts" / "draft_v4.jpg").convert("RGB")
    s = draft.width / 600  # draft px per mm

    # ── 1. 브랜드 (80–370) ─────────────────────────────
    logo = draft.crop((int(180 * s), int(100 * s), int(412 * s), int(262 * s)))
    logo = logo.resize((mm(200), int(mm(200) * logo.height / logo.width)), Image.LANCZOS)
    mask = Image.fromarray((np.asarray(logo.convert("L")) < 200).astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(1))
    canvas.paste(logo, (cx - logo.width // 2, mm(80)), mask)
    fy = mm(240)
    for i, c in enumerate((GREEN, (246, 246, 246), RED)):
        d.rectangle((cx - mm(75) + i * mm(50), fy, cx - mm(25) + i * mm(50), fy + mm(14)), fill=c)
    d.text((cx, mm(300)), "이탈리아 정품 노지 화분", font=font("Bold", 42), fill=INK, anchor="mm")
    d.text((cx, mm(350)), "튼튼하게, 유연하게, 잘 통하게", font=font("Bold", 20), fill=SUB, anchor="mm")

    # ── 2. 핵심 근거 패널 (390–690) ─────────────────────
    d.rectangle((L, mm(390), R, mm(690)), fill=PANEL)
    placeholder(d, (L + mm(20), mm(410), L + mm(250), mm(670)), "지게차 테스트 사진")
    tx = L + mm(275)
    d.text((tx, mm(430)), "01  압도적 내구성", font=font("Bold", 14), fill=(90, 200, 130), anchor="lm")
    d.text((tx - mm(3), mm(515)), "3톤", font=font("Bold", 95), fill=(255, 255, 255), anchor="lm")
    d.text((tx, mm(600)), "지게차 테스트", font=font("Bold", 24), fill=(255, 255, 255), anchor="lm")
    d.text((tx, mm(640)), "파손 ZERO", font=font("Bold", 24), fill=(90, 200, 130), anchor="lm")

    # ── 3. 특징 (720–1240): 사진 + 글, 좌우 번갈아 ────────
    feats = [
        ("02", "프리미엄 소재", ["가볍고 유연한 PE-LD 04 소재", "충격에도 깨지지 않아요"],
         POTS / "Container with top handle/Still life/Container with top handle - front.png"),
        ("03", "탁월한 배수", ["바닥 전면 다공 배수 설계", "통기성·배수성 우수"],
         POTS / "Marsili/Still life/Marsili - bottom.png"),
        ("04", "통기 받침 구조", ["바닥이 지면에서 떠 있어", "뿌리까지 공기가 통해요"],
         POTS / "Etna/Still life/Etna - bottom.jpeg"),
    ]
    y = mm(720)
    row_h = mm(170)
    for i, (num, title, desc, img_path) in enumerate(feats):
        card_w, card_h = mm(220), mm(150)
        left_photo = i % 2 == 0
        px = L if left_photo else R - card_w
        d.rectangle((px, y, px + card_w, y + card_h), fill=(255, 255, 255))
        photo = fit(Image.open(img_path).convert("RGBA"), card_w - mm(24), card_h - mm(20))
        paste_rgba(canvas, photo, (px + (card_w - photo.width) // 2, y + (card_h - photo.height) // 2))
        tx = px + card_w + mm(28) if left_photo else L
        ty = y + mm(28)
        d.text((tx, ty), num, font=font("Bold", 13), fill=GREEN, anchor="lm")
        d.text((tx, ty + mm(36)), title, font=font("Bold", 26), fill=INK, anchor="lm")
        for j, line in enumerate(desc):
            d.text((tx, ty + mm(80) + j * mm(26)), line, font=font("Medium", 15), fill=SUB, anchor="lm")
        y += row_h + (mm(4) if i < 2 else 0)

    # ── 4. 제품 라인업 (1260–1500) ─────────────────────
    d.line((L, mm(1255), R, mm(1255)), fill=LINE, width=2)
    d.text((cx, mm(1285)), "제품 라인업", font=font("Bold", 20), fill=INK, anchor="mm")
    line_pots = [
        ("Container", POTS / "Container with top handle/Still life/Container with top handle - front.png"),
        ("Marsili", POTS / "Marsili/Still life/Marsili - front.png"),
        ("Etna", OUT / "cache" / "Etna - front_cut.png"),
    ]
    col = (R - L) // 3
    base = mm(1440)
    for i, (name, p) in enumerate(line_pots):
        im = Image.open(p).convert("RGBA")
        im = im.crop(im.getbbox())
        im = fit(im, col - mm(30), mm(120))
        x = L + col * i + (col - im.width) // 2
        paste_rgba(canvas, im, (x, base - im.height))
        d.text((L + col * i + col // 2, mm(1462)), name, font=font("Bold", 16), fill=INK, anchor="mm")
        d.text((L + col * i + col // 2, mm(1488)), "○○L · Ø○○cm", font=font("Medium", 12), fill=SUB, anchor="mm")

    # ── 5. 현장 사진 띠 (1510–1620) ────────────────────
    field = [POTS / "Etna/Set photos/Etna_1.jpeg", POTS / "Marsili/Set Photo/Marsili.jpg", POTS / "Etna/Set photos/Etna_2.jpeg"]
    gap = mm(8)
    fw = (R - L - gap * 2) // 3
    for i, p in enumerate(field):
        im = cover(Image.open(p).convert("RGB"), fw, mm(90))
        canvas.paste(im, (L + i * (fw + gap), mm(1510)))
    d.text((cx, mm(1618)), "농장 · 조경 현장에서 쓰는 화분", font=font("Medium", 12), fill=SUB, anchor="mm")

    # ── 6. 하단: QR · 연락처 · 오픈가든 (1640–1725) ─────
    placeholder(d, (L, mm(1640), L + mm(80), mm(1720)), "QR")
    d.text((L + mm(95), mm(1665)), "지게차 테스트 영상 보기", font=font("Bold", 15), fill=INK, anchor="lm")
    d.text((L + mm(95), mm(1695)), "문의 010-0000-0000", font=font("Medium", 12), fill=SUB, anchor="lm")
    og = draft.crop((int(135 * s), int(1532 * s), int(465 * s), int(1666 * s)))
    og = og.resize((mm(170), int(mm(170) * og.height / og.width)), Image.LANCZOS)
    ogm = Image.fromarray((np.asarray(og.convert("L")) < 150).astype(np.uint8) * 255)
    canvas.paste(og, (R - og.width, mm(1650)), ogm)

    out = canvas.convert("RGB")
    out.save(OUT / "info_banner_mockup.jpg", quality=92)

    # 구역 표시 버전
    ann = out.copy().convert("RGBA")
    layer = Image.new("RGBA", ann.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    zones = [("브랜드", 70, 370), ("핵심 근거", 390, 690), ("특징 3개", 720, 1240), ("라인업", 1255, 1500),
             ("현장 사진", 1505, 1625), ("QR · 연락처", 1635, 1725)]
    for name, a, b in zones:
        ld.rectangle((0, mm(a), W - 1, mm(b)), outline=(214, 40, 40, 255), width=3)
        ld.rectangle((0, mm(a), mm(120), mm(a) + mm(22)), fill=(214, 40, 40, 230))
        ld.text((mm(6), mm(a) + mm(11)), f"{name} {a}–{b}", font=font("Bold", 9), fill=(255, 255, 255, 255), anchor="lm")
    for a, b in ((0, 70), (1730, 1800)):
        ld.rectangle((0, mm(a), W, mm(b)), fill=(214, 40, 40, 50))
    Image.alpha_composite(ann, layer).convert("RGB").save(OUT / "info_banner_mockup_zones.jpg", quality=90)
    print("saved info_banner_mockup.jpg, info_banner_mockup_zones.jpg")


if __name__ == "__main__":
    main()
