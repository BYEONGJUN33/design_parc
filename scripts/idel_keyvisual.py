"""IDeL 세로 현수막 키비주얼 합성 (참고: 불가리 스틸라이프 — 밝은 회백색 스튜디오).

원칙
  - 화분 원본 픽셀은 크기 축소 외에 손대지 않는다 (색·대비·광택·그레인 X).
  - 접지: 화분 실루엣의 바닥 곡선에서 바닥 타원을 직접 계산해 그 아래를 어둡게.
  - 그림자: 왼쪽에서 들어오는 빛 → 오른쪽 앞으로 떨어지는 선명한 그림자.

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

# ---- palette: 참고 사진 2 (차가운 회백색) ----
WALL_TOP = np.array([0.80, 0.82, 0.85])
WALL_BOTTOM = np.array([0.90, 0.91, 0.92])
FLOOR_BACK = np.array([0.95, 0.95, 0.96])
FLOOR_FRONT = np.array([0.88, 0.89, 0.90])
SHADOW = np.array([0.50, 0.53, 0.58])      # 그림자에 곱하는 값 (살짝 푸른 회색)

# ---- layout (비율 0~1) ----
HORIZON_Y = 0.560          # 벽과 바닥이 만나는 선
# (파일, 가로 중심 x, 바닥 가장 아랫점 y, 가로폭) — 뒤에 있는 것부터
POTS = [
    ("Etna/Still life/Etna - front.jpeg", 0.74, 0.640, 0.30),
    ("Container with top handle/Still life/Container with top handle - front.png", 0.28, 0.660, 0.40),
    ("Marsili/Still life/Marsili - front.png", 0.52, 0.745, 0.42),
]

# ---- light: 왼쪽 위에서 → 그림자는 오른쪽, 살짝 앞으로 ----
KX, KY = 0.85, -0.16       # 높이 h의 단면이 바닥에 떨어지는 위치 (x + h*KX, y - h*KY)


def load_pot(rel, cache_dir):
    path = SRC / rel
    im = Image.open(path)
    if im.mode != "RGB":
        rgba = np.asarray(im.convert("RGBA")).astype(np.float32) / 255
        if rgba[..., 3].min() < 0.5:
            return rgba
    # 흰 배경 사진 → 누끼 (마스크만 새로 만들고 색은 원본 그대로)
    cached = cache_dir / (path.stem + "_cut.png")
    if not cached.exists():
        from rembg import new_session, remove
        cut = remove(Image.open(path).convert("RGB"), session=new_session("isnet-general-use"))
        cut.save(cached)
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255
    a = np.asarray(Image.open(cached).convert("RGBA"))[..., 3].astype(np.float32) / 255
    solid = ndi.binary_fill_holes(a > 0.5)
    lab, n = ndi.label(solid)
    if n > 1:
        solid = lab == (1 + int(np.argmax(ndi.sum(solid, lab, range(1, n + 1)))))
    # 가장자리 1~2px만: 흰 배경이 섞인 픽셀을 바로 안쪽 색으로 (흰 테두리 방지)
    soft = np.clip(ndi.gaussian_filter(solid.astype(np.float32), 0.7), 0, 1)
    inner = ndi.grey_erosion(rgb, size=(5, 5, 1))
    edge = (soft > 0) & (soft < 1)
    rgb = rgb.copy()
    rgb[edge] = inner[edge]
    return np.dstack([rgb, soft])


def trim(rgba):
    ys, xs = np.nonzero(rgba[..., 3] > 0.02)
    return rgba[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]


def resize(rgba, w):
    h = round(rgba.shape[0] * w / rgba.shape[1])
    im = Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
    return np.asarray(im.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255


def footprint(a):
    """실루엣 바닥 곡선에서 바닥 원 (cx, cy, rx, ry) — 화분 이미지 좌표.

    가운데에서 바깥으로 가며 바닥 외곽선의 기울기가 급해지는 지점(= 옆면이 시작되는 곳)을
    바닥 원의 양 끝으로 본다. rx = 양 끝 사이 반폭, cy = 양 끝 높이, ry = 가장 아랫점 - cy.
    """
    solid = a > 0.5
    h, w = solid.shape
    has = solid.any(0)
    bottom = np.where(has, h - 1 - np.argmax(solid[::-1], 0), 0).astype(np.float32)
    # 받침 발 사이 홈은 무시: 아래쪽 외곽선만 + 살짝 매끄럽게
    bottom = ndi.maximum_filter1d(bottom, size=max(3, w // 12))
    bottom = ndi.uniform_filter1d(bottom, size=max(3, w // 40))
    base = bottom.max()
    xs = np.nonzero(has)[0]
    cx = int((xs.min() + xs.max()) / 2)
    slope = np.abs(np.gradient(bottom))

    def end(direction):
        x = cx
        while 0 < x < w - 1 and slope[x] < 1.5:
            x += direction
        return x

    xl, xr = end(-1), end(+1)
    rx = (xr - xl) / 2
    cy = (bottom[xl] + bottom[xr]) / 2
    return (xl + xr) / 2, float(cy), float(rx), float(max(2.0, base - cy))


def ellipse_mask(H, W, cx, cy, rx, ry):
    m = np.zeros((H, W), np.float32)
    y0, y1 = max(0, int(cy - ry)), min(H, int(cy + ry) + 2)
    x0, x1 = max(0, int(cx - rx)), min(W, int(cx + rx) + 2)
    if y0 < y1 and x0 < x1:
        yy, xx = np.ogrid[y0:y1, x0:x1]
        m[y0:y1, x0:x1] = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    return m


def build_background(W, H, rng):
    img = np.zeros((H, W, 3), np.float32)
    hy = int(H * HORIZON_Y)
    # 벽: 위는 어둡고 아래로 밝아짐 + 왼쪽 위에서 들어오는 부드러운 빛줄기
    t = np.linspace(0, 1, hy)[:, None, None]
    wall = WALL_TOP * (1 - t) + WALL_BOTTOM * t
    yy, xx = np.mgrid[0:hy, 0:W].astype(np.float32)
    beam = np.exp(-(((xx / W) * 0.9 + (yy / H) * 1.6 - 0.25) ** 2) / 0.02)
    img[:hy] = wall * (1 + 0.10 * beam[..., None])
    # 바닥: 벽 쪽은 밝고 앞으로 올수록 살짝 어두움
    fh = H - hy
    t = np.linspace(0, 1, fh)[:, None, None] ** 0.8
    img[hy:] = FLOOR_BACK * (1 - t) + FLOOR_FRONT * t
    # 벽과 바닥 경계를 살짝 부드럽게
    b = max(2, H // 800)
    img[hy - 4 * b: hy + 4 * b] = ndi.gaussian_filter1d(img[hy - 4 * b: hy + 4 * b], b, axis=0)
    # 인쇄 시 계조 끊김 방지용 미세 노이즈 (배경에만)
    img += rng.normal(0, 0.004, (H, W, 1)).astype(np.float32)
    return img


def cast_shadow(H, W, pot, x0, y0, fp):
    """화분을 가로 단면(타원)들의 묶음으로 보고 각 단면의 그림자를 바닥에 찍는다."""
    ph, pw = pot.shape[:2]
    fcx, fcy, frx, fry = fp
    ratio = fry / max(1.0, frx)            # 이 화분 사진의 원근(바닥 타원 납작함)
    solid = pot[..., 3] > 0.5
    cols = np.arange(pw)
    base_row = fcy                          # 바닥 타원 중심 높이가 그림자의 시작점
    canvas = np.zeros((H, W), np.float32)
    step = max(1, ph // 200)
    for row in range(int(base_row), -1, -step):
        xs = cols[solid[row]]
        if xs.size == 0:
            continue
        h = base_row - row
        rx = max(1.0, (xs[-1] - xs[0]) / 2)
        cx = x0 + (xs[0] + xs[-1]) / 2 + h * KX
        cy = y0 + fcy - h * KY
        np.maximum(canvas, ellipse_mask(H, W, cx, cy, rx, max(1.0, rx * ratio)), out=canvas)
    # 가까운 곳은 선명, 멀어질수록 흐리고 옅게
    near = ndi.gaussian_filter(canvas, max(0.8, pw * 0.003))
    far = ndi.gaussian_filter(canvas, max(1.0, pw * 0.02))
    dist = np.clip((np.arange(W)[None, :] - (x0 + fcx)) / max(1.0, ph * KX), 0, 1)
    out = near * (1 - dist) + far * dist
    out *= 1 - 0.35 * dist
    out[: int(H * HORIZON_Y)] = 0
    return out


def contact_shadow(H, W, pot, x0, y0, fp):
    """화분 바닥 외곽선에 딱 붙는 진한 접지 그림자 + 바닥 원 주변의 옅은 앰비언트 그림자."""
    ph, pw = pot.shape[:2]
    fcx, fcy, frx, fry = fp
    # 1) 실루엣을 아래로 조금 내린 모양 → 바닥 곡선(발 포함) 바로 밑에만 진하게
    sil = np.zeros((H, W), np.float32)
    d = max(1, round(ph * 0.004))
    ys, ye = max(0, y0 + d), min(H, y0 + d + ph)
    xs, xe = max(0, x0), min(W, x0 + pw)
    sil[ys:ye, xs:xe] = pot[ys - y0 - d: ye - y0 - d, xs - x0: xe - x0, 3]
    sil[: int(y0 + fcy)] = 0                       # 바닥 원 중심보다 위(화분 몸통)는 제외
    tight = ndi.gaussian_filter(sil, max(0.8, ph * 0.004))
    # 2) 바닥 원 주변 옅은 그림자 (화분 폭 안쪽으로 제한)
    wide = ellipse_mask(H, W, x0 + fcx, y0 + fcy + fry * 0.15, frx * 0.98, fry * 1.25)
    wide = ndi.gaussian_filter(wide, max(1.0, pw * 0.02))
    return np.clip(0.95 * tight + 0.30 * wide, 0, 1)


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
        src = trim(load_pot(rel, cache))
        # 원본보다 크게 배치하면 뭉개지므로 금지 (인쇄 해상도 기준 검사)
        if round(FULL_W * wf) > src.shape[1]:
            raise SystemExit(f"{rel}: 원본 {src.shape[1]}px < 배치 {round(FULL_W * wf)}px — 가로폭을 줄이세요")
        pot = resize(src, round(W * wf))
        fp = footprint(pot[..., 3])
        x0 = round(W * cx - fp[0])
        y0 = round(H * by - (fp[1] + fp[3]))
        placed.append((pot, x0, y0, fp))

    # 1) 긴 그림자 (모두 합쳐 한 번만 어둡게)
    sh = np.zeros((H, W), np.float32)
    for pot, x0, y0, fp in placed:
        np.maximum(sh, cast_shadow(H, W, pot, x0, y0, fp), out=sh)
    img *= 1 - 0.85 * sh[..., None] * (1 - SHADOW)

    # 2) 뒤에서부터: 접지 그림자 → 화분 원본
    for pot, x0, y0, fp in placed:
        ph, pw = pot.shape[:2]
        c = contact_shadow(H, W, pot, x0, y0, fp)
        img *= 1 - c[..., None] * (1 - SHADOW * 0.55)
        ys, ye = max(0, y0), min(H, y0 + ph)
        xs, xe = max(0, x0), min(W, x0 + pw)
        p = pot[ys - y0: ye - y0, xs - x0: xe - x0]
        a = p[..., 3:4]
        img[ys:ye, xs:xe] = p[..., :3] * a + img[ys:ye, xs:xe] * (1 - a)

    out = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    OUT.mkdir(exist_ok=True)
    name = "idel_keyvisual_full" if args.full else "idel_keyvisual_preview"
    if args.full:
        out.save(OUT / f"{name}.png", dpi=(150, 150))
    out.save(OUT / f"{name}.jpg", quality=95, subsampling=0, dpi=(150, 150))
    print("saved", OUT / name, out.size)


if __name__ == "__main__":
    main()
