"""설명형 배너 레이아웃을 Canva에서 편집 가능한 PDF로 내보내기.

  python scripts/info_banner_canva.py
  node   scripts/render_pdf.mjs output/canva/info_banner.html output/canva/info_banner.pdf 600 1800

info_banner_mockup.py 와 같은 좌표(mm)를 쓰되, 글자는 실제 텍스트·사진은 개별 이미지·면은 도형으로 둔다.
PDF를 Canva로 가져오면 각 요소를 따로 옮기고 고칠 수 있다.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
POTS = A / "IDeL 화분 사진"
OUT = ROOT / "output"
DST = OUT / "canva"
IMG = DST / "img"

L, R = 40, 560
INK, SUB, LINE = "#1E2023", "#5F646A", "#BEC2C7"
GREEN, RED, LIGHT_GREEN = "#009246", "#CE2B37", "#5AC882"
PANEL, PH = "#1E2023", "#464A50"
DPMM = 150 / 25.4           # 150dpi 기준 px/mm


def px(mm_):
    return int(round(mm_ * DPMM))


def save_png(im, name):
    im.save(IMG / name, optimize=True)
    return f"img/{name}"


def fit_png(path, name, w_mm, h_mm):
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getbbox())
    im.thumbnail((px(w_mm), px(h_mm)), Image.LANCZOS)
    return save_png(im, name), im.width / DPMM, im.height / DPMM


def masked_crop(draft, box_mm, thr, name, width_mm):
    s = draft.width / 600
    x0, y0, x1, y1 = box_mm
    im = draft.crop((int(x0 * s), int(y0 * s), int(x1 * s), int(y1 * s)))
    im = im.resize((px(width_mm), int(px(width_mm) * im.height / im.width)), Image.LANCZOS)
    a = Image.fromarray((np.asarray(im.convert("L")) < thr).astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(1))
    im = im.convert("RGBA")
    im.putalpha(a)
    return save_png(im, name), width_mm, width_mm * im.height / im.width


def text(x, y, s, glyph_mm, color, weight=700, anchor="mm", width=None):
    """PIL 버전과 같은 기준점: anchor mm = 가운데, lm = 왼쪽 가운데."""
    fs = glyph_mm / 0.78
    style = f"font-size:{fs:.2f}mm;line-height:{fs:.2f}mm;color:{color};font-weight:{weight};top:{y - fs / 2:.2f}mm;"
    if anchor == "mm":
        w = width or 520
        style += f"left:{x - w / 2:.2f}mm;width:{w}mm;text-align:center;"
    else:
        style += f"left:{x:.2f}mm;"
    return f'<div class="t" style="{style}">{s}</div>'


def rect(x0, y0, x1, y1, color, extra=""):
    return f'<div class="r" style="left:{x0}mm;top:{y0}mm;width:{x1 - x0}mm;height:{y1 - y0}mm;background:{color};{extra}"></div>'


def img(src, x, y, w, h, fit="contain"):
    return f'<img src="{src}" style="left:{x:.2f}mm;top:{y:.2f}mm;width:{w:.2f}mm;height:{h:.2f}mm;object-fit:{fit};">'


def placeholder(x0, y0, x1, y1, label):
    return rect(x0, y0, x1, y1, PH) + text((x0 + x1) / 2, (y0 + y1) / 2, label, 13, "#C8CCD2", 700, "mm", x1 - x0)


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    draft = Image.open(A / "drafts" / "draft_v4.jpg").convert("RGB")
    el = []
    cx = 300

    # 배경
    Image.open(OUT / "bg_plain.jpg").save(IMG / "bg_plain.jpg", quality=92)
    el.append(img("img/bg_plain.jpg", 0, 0, 600, 1800, "fill"))

    # 1. 브랜드
    src, w, h = masked_crop(draft, (180, 100, 412, 262), 200, "logo_idel_lowres.png", 200)
    el.append(img(src, cx - w / 2, 80, w, h))
    for i, c in enumerate((GREEN, "#F6F6F6", RED)):
        el.append(rect(cx - 75 + i * 50, 240, cx - 25 + i * 50, 254, c))
    el.append(text(cx, 300, "이탈리아 정품 노지 화분", 42, INK))
    el.append(text(cx, 350, "튼튼하게, 유연하게, 잘 통하게", 20, SUB))

    # 2. 핵심 근거 패널
    el.append(rect(L, 390, R, 690, PANEL))
    el.append(placeholder(L + 20, 410, L + 250, 670, "지게차 테스트 사진"))
    tx = L + 275
    el.append(text(tx, 430, "01&nbsp;&nbsp;압도적 내구성", 14, LIGHT_GREEN, 700, "lm"))
    el.append(text(tx - 3, 515, "3톤", 95, "#FFFFFF", 700, "lm"))
    el.append(text(tx, 600, "지게차 테스트", 24, "#FFFFFF", 700, "lm"))
    el.append(text(tx, 640, "파손 ZERO", 24, LIGHT_GREEN, 700, "lm"))

    # 3. 특징 3개
    feats = [
        ("02", "프리미엄 소재", ["가볍고 유연한 PE-LD 04 소재", "충격에도 깨지지 않아요"],
         POTS / "Container with top handle/Still life/Container with top handle - front.png"),
        ("03", "탁월한 배수", ["바닥 전면 다공 배수 설계", "통기성·배수성 우수"],
         POTS / "Marsili/Still life/Marsili - bottom.png"),
        ("04", "통기 받침 구조", ["바닥이 지면에서 떠 있어", "뿌리까지 공기가 통해요"],
         POTS / "Etna/Still life/Etna - bottom.jpeg"),
    ]
    y = 720
    for i, (num, title, desc, p) in enumerate(feats):
        cw, ch = 220, 150
        left_photo = i % 2 == 0
        x0 = L if left_photo else R - cw
        el.append(rect(x0, y, x0 + cw, y + ch, "#FFFFFF"))
        src, w, h = fit_png(p, f"feature_{num}.png", cw - 24, ch - 20)
        el.append(img(src, x0 + (cw - w) / 2, y + (ch - h) / 2, w, h))
        tx = x0 + cw + 28 if left_photo else L
        ty = y + 28
        el.append(text(tx, ty, num, 13, GREEN, 700, "lm"))
        el.append(text(tx, ty + 36, title, 26, INK, 700, "lm"))
        for j, line in enumerate(desc):
            el.append(text(tx, ty + 80 + j * 26, line, 15, SUB, 500, "lm"))
        y += 170 + (4 if i < 2 else 0)

    # 4. 제품 라인업
    el.append(rect(L, 1254.5, R, 1255.5, LINE))
    el.append(text(cx, 1285, "제품 라인업", 20, INK))
    pots = [("Container", POTS / "Container with top handle/Still life/Container with top handle - front.png"),
            ("Marsili", POTS / "Marsili/Still life/Marsili - front.png"),
            ("Etna", OUT / "cache" / "Etna - front_cut.png")]
    col = (R - L) / 3
    for i, (name, p) in enumerate(pots):
        src, w, h = fit_png(p, f"lineup_{name}.png", col - 30, 120)
        ccx = L + col * i + col / 2
        el.append(img(src, ccx - w / 2, 1440 - h, w, h))
        el.append(text(ccx, 1462, name, 16, INK, 700, "mm", col))
        el.append(text(ccx, 1488, "○○L · Ø○○cm", 12, SUB, 500, "mm", col))

    # 5. 현장 사진
    field = [POTS / "Etna/Set photos/Etna_1.jpeg", POTS / "Marsili/Set Photo/Marsili.jpg", POTS / "Etna/Set photos/Etna_2.jpeg"]
    gap = 8
    fw = (R - L - gap * 2) / 3
    for i, p in enumerate(field):
        im = ImageOps.fit(Image.open(p).convert("RGB"), (px(fw), px(90)), Image.LANCZOS, centering=(0.5, 0.55))
        im.save(IMG / f"field_{i + 1}.jpg", quality=90)
        el.append(img(f"img/field_{i + 1}.jpg", L + i * (fw + gap), 1510, fw, 90, "fill"))
    el.append(text(cx, 1618, "농장 · 조경 현장에서 쓰는 화분", 12, SUB, 500))

    # 6. 하단
    el.append(placeholder(L, 1640, L + 80, 1720, "QR"))
    el.append(text(L + 95, 1665, "지게차 테스트 영상 보기", 15, INK, 700, "lm"))
    el.append(text(L + 95, 1695, "문의 010-0000-0000", 12, SUB, 500, "lm"))
    src, w, h = masked_crop(draft, (135, 1532, 465, 1666), 150, "logo_opengarden_lowres.png", 170)
    el.append(img(src, R - w, 1650, w, h))

    fonts = "".join(
        f'@font-face{{font-family:Pretendard;font-weight:{wgt};src:url(../../fonts/Pretendard-{n}.woff2) format("woff2");}}'
        for wgt, n in ((500, "Medium"), (700, "Bold")))
    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
{fonts}
@page {{ size: 600mm 1800mm; margin: 0; }}
html, body {{ margin:0; padding:0; }}
body {{ width:600mm; height:1800mm; position:relative; overflow:hidden; font-family:Pretendard, sans-serif; }}
.t, .r, img {{ position:absolute; margin:0; white-space:nowrap; letter-spacing:-0.01em; }}
</style></head><body>
{chr(10).join(el)}
</body></html>"""
    (DST / "info_banner.html").write_text(html, encoding="utf-8")
    print("saved", DST / "info_banner.html")


if __name__ == "__main__":
    main()
