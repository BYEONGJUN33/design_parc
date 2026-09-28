# design_parc

현수막·웹사이트·각종 디자인 작업 공간입니다.
AI가 새로 만든 레이아웃 대신, **사람이 직접 만든 공개 템플릿**을 기반으로 작업합니다.

## 폴더 구성

| 폴더 | 내용 |
|---|---|
| `assets/` | 작업 소스 (누끼 딴 이미지, 참고 사진, 로고 등) |
| `scripts/` | 합성 스크립트 |
| `output/` | 결과물 (미리보기·인쇄용) |
| `fonts/` | [Pretendard](https://github.com/orioncactus/pretendard) 한글 폰트 (SIL OFL, 상업적 사용 무료) |

## IDeL 세로 현수막 키비주얼

참고 사진(`assets/Idel_Pots_reference`)의 불가리 스틸라이프(밝은 회백색 스튜디오) 스타일로 누끼 화분을 합성합니다.
화분 원본 픽셀은 크기 축소 외에 손대지 않고, 바닥 곡선에 맞춘 접지 그림자와 왼쪽 빛의 긴 그림자만 더합니다.

```bash
pip install -r scripts/requirements.txt
python scripts/idel_keyvisual.py          # 미리보기 → output/idel_keyvisual_preview.jpg
python scripts/idel_keyvisual.py --full   # 600×1800mm @150dpi → output/idel_keyvisual_full.png / .jpg
```

화분 위치·크기, 벽·바닥 경계, 그림자 방향, 색은 `scripts/idel_keyvisual.py` 상단의 `POTS`, `HORIZON_Y`, `KX`·`KY`(그림자 방향), 팔레트 값으로 조정합니다.

---

## 리서치 메모

### 사람이 만든 세로 현수막 템플릿을 찾을 수 있는 곳

GitHub 오픈소스에는 인쇄용 현수막 템플릿이 거의 없습니다.
(Penpot 공식 공개 파일 [penpot/penpot-files](https://github.com/penpot/penpot-files) 157개도 대부분 UI 키트·아이콘이고, 인쇄물은 전단지 튜토리얼 1개뿐.)
사람이 직접 만든 세로 현수막 템플릿은 아래 플랫폼에 모여 있습니다.

| 플랫폼 | 특징 | 배경 제거 | AI(Claude) 연동 |
|---|---|---|---|
| Canva | 디자이너 제작 세로 배너·포스터 템플릿 다수 | 있음 | Canva 커넥터로 디자인 읽기·수정 가능 |
| 미리캔버스 | 한국형 세로 현수막·X배너 템플릿 최다, 인쇄 주문 연계 | 있음 | 없음 |

### 직접 편집하는 오픈소스 디자인 툴

| 리포지토리 | 특징 | AI 연동 |
|---|---|---|
| [penpot/penpot](https://github.com/penpot/penpot) | 오픈소스 Figma 대안, SVG 기반 | 공식 MCP [penpot/penpot-mcp](https://github.com/penpot/penpot-mcp) |
| [GraphiteEditor/Graphite](https://github.com/GraphiteEditor/Graphite) | 벡터·래스터 그래픽 편집기 | 없음 |

### 누끼(배경 제거)

| 리포지토리 | 특징 |
|---|---|
| [danielgatis/rembg](https://github.com/danielgatis/rembg) | 가장 널리 쓰이는 배경 제거 도구 (Python, 명령 한 줄) |
| [imgly/background-removal-js](https://github.com/imgly/background-removal-js) | 브라우저에서 설치 없이 배경 제거 |

### 영상 (추후)

| 리포지토리 | 특징 |
|---|---|
| [remotion-dev/remotion](https://github.com/remotion-dev/remotion) | React 코드로 영상 제작 |
