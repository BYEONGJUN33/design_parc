"""원거리용 세로 현수막 보강 시안 (사용자 시안 far_v1 비율 415:963).

  python scripts/far_banner_concept.py → output/far_banner_concept.jpg

로고·화분 사진은 사용자 시안(저해상도)에서 가져온 것이라 구성 확인용이다.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
C = OUT / "cache"
W, H = 1660, 3852                      # 시안 415x963 의 4배
INK, SUB, GREEN, RED, BAND = (24, 26, 29), (80, 85, 92), (0, 146, 70), (206, 43, 55), (30, 32, 35)


def f(weight, px):
    return ImageFont.truetype(str(C / f"Pretendard-{weight}.otf"), int(px))


def pot_cutout():
    im = Image.open(C / "far_pot_cut.png").convert("RGBA")
    a = np.asarray(im)[..., 3] > 128
    lab, n = ndi.label(a)
    keep = lab == (1 + int(np.argmax(ndi.sum(a, lab, range(1, n + 1)))))   # 손 잔여물 제거
    keep = ndi.binary_fill_holes(keep) & a | keep
    alpha = Image.fromarray((keep * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    im.putalpha(alpha)
    return im.crop(im.getbbox())


def background():
    y = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([222, 225, 229]), np.array([238, 239, 241])
    bg = (top * (1 - y) + bot * y) * np.ones((1, W, 1))
    return Image.fromarray(bg.astype(np.uint8)).convert("RGBA")


def build(variant):
    im = background()
    d = ImageDraw.Draw(im)
    cx = W // 2

    draft = Image.open(ROOT / "assets/drafts/far_v1.png").convert("RGB")
    logo = draft.crop((122, 18, 286, 134)).resize((164 * 4, 116 * 4), Image.LANCZOS)
    m = Image.fromarray((np.asarray(logo.convert("L")) < 190).astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(1.5))
    im.paste(logo, (cx - logo.width // 2, 70), m)

    fy = int(H * 0.152)
    for i, c in enumerate((GREEN, (248, 248, 248), RED)):
        d.rectangle((cx - 300 + i * 200, fy, cx - 100 + i * 200, fy + 52), fill=c)

    # 헤드라인: 한 가지 굵은 고딕, No.1만 강조색
    hf = f("Black", 330)
    a, b = "유럽 ", "No.1"
    wa, wb = d.textlength(a, font=hf), d.textlength(b, font=hf)
    x0 = cx - (wa + wb) / 2
    hy = int(H * 0.232)
    d.text((x0, hy), a, font=hf, fill=INK, anchor="lm")
    d.text((x0 + wa, hy), b, font=hf, fill=GREEN, anchor="lm")
    d.text((cx, int(H * 0.318)), "이탈리아 프리미엄 화분", font=f("ExtraBold", 150), fill=INK, anchor="mm")

    # 제품 + 배경 원
    pot = pot_cutout()
    pw = int(W * 0.84)
    pot = pot.resize((pw, int(pw * pot.height / pot.width)), Image.LANCZOS)
    pcy = int(H * 0.585)
    r = int(W * 0.47)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    if variant == "circle":
        ld.ellipse((cx - r, pcy - r, cx + r, pcy + r), fill=GREEN + (255,))
    else:
        glow = Image.new("L", im.size, 0)
        ImageDraw.Draw(glow).ellipse((cx - r, pcy - r, cx + r, pcy + r), fill=255)
        glow = glow.filter(ImageFilter.GaussianBlur(160))
        layer = Image.merge("RGBA", [Image.new("L", im.size, 255)] * 3 + [glow.point(lambda v: int(v * 0.85))])
    im = Image.alpha_composite(im, layer)
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sa = pot.getchannel("A").point(lambda v: int(v * 0.45))
    shadow.paste(Image.new("RGBA", pot.size, (0, 0, 0, 255)), (cx - pw // 2 + 30, pcy - pot.height // 2 + 50), sa)
    im = Image.alpha_composite(im, shadow.filter(ImageFilter.GaussianBlur(40)))
    im.alpha_composite(pot, (cx - pw // 2, pcy - pot.height // 2))

    # 하단 근거 띠
    d = ImageDraw.Draw(im)
    y0, y1 = int(H * 0.815), int(H * 0.925)
    d.rectangle((0, y0, W, y1), fill=BAND)
    d.text((cx, y0 + (y1 - y0) * 0.30), "3톤 지게차에도", font=f("ExtraBold", 132), fill=(255, 255, 255), anchor="mm")
    d.text((cx, y0 + (y1 - y0) * 0.70), "파손 ZERO", font=f("Black", 196), fill=(90, 200, 130), anchor="mm")

    og = Image.open(ROOT / "assets/drafts/draft_v4.jpg").convert("RGB")
    s = og.width / 600
    og = og.crop((int(135 * s), int(1532 * s), int(465 * s), int(1666 * s)))
    og = og.resize((560, int(560 * og.height / og.width)), Image.LANCZOS)
    om = Image.fromarray((np.asarray(og.convert("L")) < 150).astype(np.uint8) * 255)
    im.paste(og, (cx - og.width // 2, int(H * 0.936)), om)
    return im.convert("RGB")


def main():
    draft = Image.open(ROOT / "assets/drafts/far_v1.png").convert("RGB").resize((W, H), Image.LANCZOS)
    a, b = build("circle"), build("glow")
    pw, ph = 560, 1300
    sheet = Image.new("RGB", (pw * 3 + 120, ph + 90), "white")
    d = ImageDraw.Draw(sheet)
    for i, (img, label) in enumerate(((draft, "지금 시안"), (a, "A안: 초록 원 + 하단 근거 띠"), (b, "B안: 은은한 조명 + 하단 근거 띠"))):
        sheet.paste(img.resize((pw, ph), Image.LANCZOS), (i * (pw + 60), 90))
        d.text((i * (pw + 60) + 4, 45), label, font=f("ExtraBold", 34), fill=INK, anchor="lm")
    sheet.save(OUT / "far_banner_concept.jpg", quality=92)
    a.save(OUT / "far_banner_A.jpg", quality=92)
    b.save(OUT / "far_banner_B.jpg", quality=92)
    print("saved far_banner_concept.jpg")


if __name__ == "__main__":
    main()
