"""IDeL 세로 현수막 키비주얼 합성.

참고 사진(assets/Idel_Pots_reference) 스타일:
  세로 줄무늬 벽 + 질감 있는 받침대 + 한쪽에서 들어오는 강한 햇빛과 긴 그림자.

  python scripts/idel_keyvisual.py            # 미리보기 (25%)
  python scripts/idel_keyvisual.py --full     # 600x1800mm @150dpi (3543x10630)
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "IDeL 화분 사진"
OUT = ROOT / "output"

FULL_W, FULL_H = 3543, 10630  # 600 x 1800 mm @ 150 dpi

# ---- palette (참고 사진 1의 따뜻한 베이지/샌드 톤) ----
WALL = np.array([0.93, 0.87, 0.77])
PLINTH_TOP = np.array([0.80, 0.64, 0.47])
PLINTH_FACE = np.array([0.55, 0.37, 0.24])
SHADOW = np.array([0.50, 0.44, 0.40])   # 그림자 부분에 곱할 값 (살짝 따뜻한 톤)
LIGHT = np.array([1.00, 0.93, 0.80])    # 햇빛 색

# ---- layout (비율, 0~1) ----
PLINTH_TOP_Y = 0.560   # 벽과 받침대 윗면이 만나는 선
PLINTH_EDGE_Y = 0.745  # 받침대 윗면과 앞면이 만나는 모서리
LIGHT_DIR = -1          # -1: 빛이 오른쪽에서 → 그림자는 왼쪽 앞으로

# (파일, 가로 중심 x, 바닥 y, 가로폭) — 뒤에 있는 것부터
POTS = [
    ("Container with top handle/Still life/Container with top handle - front.png", 0.30, 0.618, 0.44),
    ("Etna/Still life/Etna - front.jpeg", 0.79, 0.636, 0.33),
    ("Marsili/Still life/Marsili - front.png", 0.60, 0.700, 0.44),
]


def fbm(h, w, rng, scales, weights):
    """부드러운 노이즈 (석고/모래 질감용)."""
    out = np.zeros((h, w), np.float32)
    for s, wt in zip(scales, weights):
        n = rng.standard_normal((max(2, h // s), max(2, w // s))).astype(np.float32)
        n = ndi.zoom(n, (h / n.shape[0], w / n.shape[1]), order=1)[:h, :w]
        out += wt * n
    return out


def load_pot(rel, cache_dir):
    path = SRC / rel
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P") and "A" in im.convert("RGBA").getbands():
        rgba = np.asarray(im.convert("RGBA")).astype(np.float32) / 255
        if rgba[..., 3].min() < 0.5:
            return rgba
    # 흰 배경 사진 → rembg로 누끼
    cached = cache_dir / (path.stem + "_cut.png")
    if not cached.exists():
        from rembg import new_session, remove
        cut = remove(Image.open(path).convert("RGB"), session=new_session("isnet-general-use"))
        cut.save(cached)
    rgba = np.asarray(Image.open(cached).convert("RGBA")).astype(np.float32) / 255
    return rgba


def clean_alpha(rgba):
    """반투명 누끼 정리: 채우고, 가장자리만 살짝 부드럽게, 흰 테두리 제거."""
    a = rgba[..., 3]
    solid = ndi.binary_fill_holes(a > 0.5)
    solid = ndi.binary_opening(solid, iterations=2)
    lab, n = ndi.label(solid)
    if n > 1:
        sizes = ndi.sum(solid, lab, range(1, n + 1))
        solid = lab == (1 + int(np.argmax(sizes)))
    soft = ndi.gaussian_filter(solid.astype(np.float32), 1.0)
    rgb = rgba[..., :3].copy()
    # 가장자리의 밝은 배경색 번짐(흰 테두리) → 안쪽 색으로 교체
    edge = (soft > 0.01) & ~ndi.binary_erosion(solid, iterations=3)
    inner = ndi.grey_erosion(rgb.max(-1), size=7)
    rgb[edge] = np.minimum(rgb[edge], inner[edge, None])
    return np.dstack([rgb, soft])


def trim(rgba):
    ys, xs = np.nonzero(rgba[..., 3] > 0.02)
    return rgba[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]


def resize(rgba, w):
    h = round(rgba.shape[0] * w / rgba.shape[1])
    im = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA")
    return np.asarray(im.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255


def build_background(W, H, rng):
    img = np.zeros((H, W, 3), np.float32)
    yt, ye = int(H * PLINTH_TOP_Y), int(H * PLINTH_EDGE_Y)

    # 벽: 세로 립(반원통) 패턴
    period = max(6, round(W / 30))
    x = np.arange(W)
    ph = (x % period) / period
    rib = 0.93 + 0.07 * np.sin(np.pi * ph) ** 0.6          # 립 둥근 면
    rib -= 0.05 * np.exp(-((ph - 0.0) ** 2) / 0.0015)       # 홈
    rib += 0.03 * np.clip(np.sin(2 * np.pi * ph + LIGHT_DIR * 1.2), 0, 1)  # 빛 받는 쪽
    yy = np.linspace(0, 1, yt)[:, None]
    xx = np.linspace(0, 1, W)[None, :]
    light = 0.86 + 0.16 * (1 - yy) * (0.6 + 0.4 * (xx if LIGHT_DIR < 0 else 1 - xx))
    light *= 1 - 0.10 * np.clip((yy - 0.75) / 0.25, 0, 1)   # 바닥 근처 살짝 어둡게
    wall = rib[None, :] * light
    img[:yt] = wall[..., None] * WALL

    # 받침대: 석고/샌드 질감을 높이맵으로 만들고 햇빛 방향으로 음영
    def stucco(h, w, fine):
        hm = fbm(h, w, rng, [max(1, W // 1800), max(2, W // 700), max(3, W // 200)], [1.0, 0.6, 0.35])
        hm += fine * np.clip(rng.standard_normal((h, w)).astype(np.float32), -2, 2)
        hm = ndi.gaussian_filter(hm, max(0.6, W / 2500))
        gx, gy = np.gradient(hm)
        relief = 1 + 0.9 * (LIGHT_DIR * -gx * 0.7 - gy * 0.7)  # 오른쪽 위에서 빛
        return np.clip(relief, 0.75, 1.25), hm

    th = ye - yt
    relief, hm = stucco(th, W, 0.25)
    t = np.linspace(0, 1, th)[:, None, None]
    top = PLINTH_TOP * (1.0 + 0.04 * t) * (1 + 0.35 * (relief[..., None] - 1)) * (1 + 0.015 * hm[..., None])
    img[yt:ye] = top

    fh = H - ye
    relief, hm = stucco(fh, W, 0.5)
    t = np.linspace(0, 1, fh)[:, None, None]
    face = PLINTH_FACE * (1.0 - 0.12 * t) * relief[..., None] * (1 + 0.02 * hm[..., None])
    img[ye:] = face

    # 벽과 바닥이 만나는 곳 살짝 어둡게 (앰비언트 오클루전)
    ao = max(2, H // 250)
    img[yt - ao: yt] *= np.linspace(1.0, 0.88, ao)[:, None, None]
    img[yt: yt + ao] *= np.linspace(0.85, 1.0, ao)[:, None, None]

    # 모서리 하이라이트
    e = max(2, H // 1500)
    img[ye - e: ye] = np.clip(img[ye - e: ye] * 1.12, 0, 1)
    return img


def cast_shadow(H, W, pot, x0, y0, base_y):
    """바닥에 눕는 긴 그림자 (햇빛이 오른쪽 뒤, 낮은 각도에서 들어온다고 가정).

    화분을 가로 단면(원)들의 묶음으로 보고, 높이 h의 단면은 바닥의
    (중심x - h*KX, base - h*KY) 위치에 타원 그림자를 만든다.
    KY < 0 이면 그림자가 앞(보는 사람 쪽)으로 떨어진다.
    """
    KX, KY = 0.95, -0.11
    FORESHORTEN = 0.16                 # 바닥 원이 화면에서 납작해 보이는 비율
    ph, pw = pot.shape[:2]
    solid = pot[..., 3] > 0.5
    cols = np.arange(pw)
    canvas = np.zeros((H, W), np.float32)
    step = max(1, ph // 160)
    for row in range(ph - 1, -1, -step):
        xs = cols[solid[row]]
        if xs.size == 0:
            continue
        h = ph - 1 - row
        cx = x0 + (xs[0] + xs[-1]) / 2 + LIGHT_DIR * h * KX
        cy = base_y - h * KY
        rx = (xs[-1] - xs[0]) / 2
        ry = max(1.0, rx * FORESHORTEN)
        y_lo, y_hi = max(0, int(cy - ry)), min(H, int(cy + ry) + 1)
        x_lo, x_hi = max(0, int(cx - rx)), min(W, int(cx + rx) + 1)
        if y_lo >= y_hi or x_lo >= x_hi:
            continue
        yy, xx = np.ogrid[y_lo:y_hi, x_lo:x_hi]
        inside = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
        # 멀수록 옅게 (거리 정보는 따로 저장해 흐림 정도에 사용)
        val = inside * (1 - 0.35 * h / ph)
        canvas[y_lo:y_hi, x_lo:x_hi] = np.maximum(canvas[y_lo:y_hi, x_lo:x_hi], val)

    # 화분에서 멀수록 흐리게 (반그림자): 가로 거리 기준으로 두 흐림을 섞음
    near = ndi.gaussian_filter(canvas, max(0.8, pw * 0.004))
    far = ndi.gaussian_filter(canvas, max(1.0, pw * 0.018))
    dist = np.abs(np.arange(W)[None, :] - (x0 + pw / 2)) / max(1, ph * KX)
    ramp = np.clip(dist, 0, 1)
    out = near * (1 - ramp) + far * ramp
    out[int(H * PLINTH_EDGE_Y):] = 0   # 모서리 넘어가는 부분은 그늘진 앞면에 묻힘
    return out


def shade_pot(pot):
    """검은 플라스틱에 햇빛 방향 하이라이트와 따뜻한 반사광."""
    rgb, a = pot[..., :3], pot[..., 3]
    h, w = a.shape
    # 원본마다 다른 색 틀어짐(초록/파랑 기) 제거 → 중립 검정으로 통일
    lum = (rgb @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    rgb = lum + 0.15 * (rgb - lum)
    # 대비 살짝 올려 입체감
    rgb = np.clip((rgb - 0.02) * 1.15, 0, 1)
    xx = np.linspace(0, 1, w)[None, :]
    lit = xx if LIGHT_DIR < 0 else 1 - xx
    grad = (lit ** 2.2)[..., None]
    rgb = rgb * (0.92 + 0.10 * grad)
    rgb = 1 - (1 - rgb) * (1 - 0.10 * grad * LIGHT)        # screen
    # 원통 하이라이트: 행마다 화분 폭 안에서의 위치(u)로 세로 광택 띠
    solid = a > 0.5
    idx = np.arange(w)[None, :]
    left = np.where(solid.any(1), np.argmax(solid, 1), 0)[:, None]
    right = np.where(solid.any(1), w - 1 - np.argmax(solid[:, ::-1], 1), 1)[:, None]
    u = np.clip((idx - left) / np.maximum(1, right - left), 0, 1)
    if LIGHT_DIR > 0:
        u = 1 - u
    band = 0.16 * np.exp(-((u - 0.80) ** 2) / 0.006) + 0.05 * np.exp(-((u - 0.30) ** 2) / 0.02)
    rgb = 1 - (1 - rgb) * (1 - band[..., None] * LIGHT)
    # 빛 쪽 가장자리 림라이트
    inside = ndi.binary_erosion(a > 0.5, iterations=max(2, w // 250))
    rim = ndi.gaussian_filter((a > 0.5).astype(np.float32) - inside, max(1, w / 400))
    rim *= lit
    rgb = 1 - (1 - rgb) * (1 - 0.35 * rim[..., None] * LIGHT)
    # 바닥 쪽은 받침대 색이 살짝 반사
    yy = np.linspace(0, 1, h)[:, None, None]
    rgb = rgb + 0.05 * np.clip((yy - 0.75) / 0.25, 0, 1) * PLINTH_TOP
    return np.dstack([np.clip(rgb, 0, 1), a])


def composite(img, pot, x0, y0):
    H, W = img.shape[:2]
    ph, pw = pot.shape[:2]
    ys, ye = max(0, y0), min(H, y0 + ph)
    xs, xe = max(0, x0), min(W, x0 + pw)
    p = pot[ys - y0: ye - y0, xs - x0: xe - x0]
    a = p[..., 3:4]
    img[ys:ye, xs:xe] = p[..., :3] * a + img[ys:ye, xs:xe] * (1 - a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()
    scale = 1.0 if args.full else 0.25
    W, H = round(FULL_W * scale), round(FULL_H * scale)
    rng = np.random.default_rng(7)
    cache = OUT / "cache"
    cache.mkdir(parents=True, exist_ok=True)

    img = build_background(W, H, rng)

    placed = []
    for rel, cx, by, wf in POTS:
        pot = trim(clean_alpha(load_pot(rel, cache)))
        pot = resize(pot, round(W * wf))
        ph, pw = pot.shape[:2]
        # 화분 바닥의 투명한 발 부분 보정: 알파가 있는 마지막 행이 바닥
        x0 = round(W * cx - pw / 2)
        base = round(H * by)
        y0 = base - ph
        placed.append((pot, x0, y0, base))

    # 1) 모든 그림자 먼저 (서로 겹쳐도 한 번만 어둡게)
    sh = np.zeros((H, W), np.float32)
    for pot, x0, y0, base in placed:
        sh = np.maximum(sh, cast_shadow(H, W, pot, x0, y0, base))
    img = img * (1 - sh[..., None] * (1 - SHADOW))

    # 2) 뒤에서부터 화분 + 접지 그림자
    for pot, x0, y0, base in placed:
        ph, pw = pot.shape[:2]
        contact = np.zeros((H, W), np.float32)
        cy, rx, ry = base - max(1, ph // 120), pw * 0.47, max(2, ph * 0.018)
        yy, xx = np.ogrid[:H, :W]
        contact[((xx - (x0 + pw / 2)) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1] = 1
        contact = ndi.gaussian_filter(contact, max(1, ph * 0.012))
        img *= (1 - 0.6 * contact[..., None])
        composite(img, shade_pot(pot), x0, y0)

    # 3) 전체 톤: 따뜻한 햇빛 그레이딩 + 필름 그레인
    img = np.clip(img, 0, 1) ** 0.97
    img = img * np.array([1.01, 1.0, 0.97])
    img += rng.normal(0, 0.012, img.shape[:2])[..., None].astype(np.float32)
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))

    OUT.mkdir(exist_ok=True)
    name = "idel_keyvisual_full" if args.full else "idel_keyvisual_preview"
    if args.full:
        out.save(OUT / f"{name}.png", dpi=(150, 150))
    out.save(OUT / f"{name}.jpg", quality=92, dpi=(150, 150))
    print("saved", OUT / name, out.size)


if __name__ == "__main__":
    main()
