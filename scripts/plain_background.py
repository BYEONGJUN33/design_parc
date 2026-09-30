"""빈 무지 배경 (600x1800mm @150dpi, 3543x10630px).

  python scripts/plain_background.py
  → output/bg_plain.png          무지 그라데이션 + 왼쪽 위 은은한 빛 (추천: 글·사진 올리기 좋음)
  → output/bg_studio_empty.png   키비주얼과 같은 벽·바닥 스튜디오 (화분 없이)
  → output/bg_preview.jpg        두 배경 미리보기

키비주얼(idel_keyvisual.py)과 같은 색을 써서 두 배너가 한 세트로 보이게 한다.
"""
import numpy as np
from PIL import Image

from idel_keyvisual import FULL_H, FULL_W, OUT, WALL_BOTTOM, WALL_TOP, build_background


def plain(W, H, rng):
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    img = WALL_TOP * (1 - t) + WALL_BOTTOM * t                      # 위는 살짝 진하게, 아래로 밝게
    img = np.broadcast_to(img, (H, W, 3)).astype(np.float32).copy()
    # 키비주얼과 같은 왼쪽 위 빛줄기 (벽 윗부분에만 은은하게)
    for y0 in range(0, H, 512):
        y1 = min(H, y0 + 512)
        yy, xx = np.mgrid[y0:y1, 0:W].astype(np.float32)
        beam = np.exp(-(((xx / W) * 0.9 + (yy / H) * 1.6 - 0.25) ** 2) / 0.02)
        img[y0:y1] *= 1 + 0.10 * beam[..., None]
    img += rng.normal(0, 0.004, (H, W, 1)).astype(np.float32)       # 인쇄 계조 끊김 방지
    return img


def save(img, name):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    im.save(OUT / name, dpi=(150, 150), optimize=True)
    return im


def main():
    rng = np.random.default_rng(7)
    a = save(plain(FULL_W, FULL_H, rng), "bg_plain.png")
    b = save(build_background(FULL_W, FULL_H, rng), "bg_studio_empty.png")
    pw, ph = 600, 1800
    sheet = Image.new("RGB", (pw * 2 + 40, ph), "white")
    sheet.paste(a.resize((pw, ph), Image.LANCZOS), (0, 0))
    sheet.paste(b.resize((pw, ph), Image.LANCZOS), (pw + 40, 0))
    sheet.save(OUT / "bg_preview.jpg", quality=90)
    print("saved bg_plain.png, bg_studio_empty.png, bg_preview.jpg")


if __name__ == "__main__":
    main()
