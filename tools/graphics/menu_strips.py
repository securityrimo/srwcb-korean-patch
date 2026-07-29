# -*- coding: utf-8 -*-
"""CB 부팅 '게임 선택' 메뉴 스트립 4개를 한글로 다시 그린다.

멤버 21 은 표준 TIM 들이 줄줄이 붙어 있는 덩어리다. 메뉴 항목 4개는 4bpp TIM 이고
픽셀 블록의 위치·크기는 TIM 헤더가 정확히 알려 준다(추측 금지).

  [2] @85056 184x24 VRAM(320, 80)  픽셀 85120~87328   제2차
  [3] @87328 184x24 VRAM(320,104)  픽셀 87392~89600   제3차
  [4] @89600 156x24 VRAM(320,128)  픽셀 89664~91536   EX
  [5] @91536 184x24 VRAM(320,  0)  픽셀 91600~93808   트레이닝 모드

이 범위를 한 바이트라도 넘기면 **다음 TIM 의 헤더**를 부수고, 그러면 그 뒤의
메뉴 창·화살표·타이틀 로고가 통째로 안 나온다.

CLUT 은 0=흰색에서 11=거의 검정까지 이어지는 노랑 램프이고 12 가 배경이다.
원본 글리프는 검은 외곽선이 없다. 침식 깊이로 보면

    깊이1(테두리)  5·6 위주, 그늘진 쪽에 9·11
    깊이2          0·1·2
    깊이3 이상     0 (흰색)

즉 **흰 코어 + 노랑 테두리 + 우하단 그늘**이다. 같은 규칙으로 한글을 그린다.
"""
from PIL import Image, ImageDraw, ImageFont

BG = 12
RIM_LIT = 6        # 테두리 (밝은 쪽)
RIM_SHADE = 9      # 테두리 (우하단 그늘)
MID = 1            # 깊이 2
CORE = 0           # 깊이 3 이상 = 흰색

# (이름, 픽셀 시작 오프셋, stride 바이트, 행 수, 한국어)
STRIPS = [
    ("s1", 85120, 92, 24, "제2차 슈퍼로봇대전"),
    ("s2", 87392, 92, 24, "제3차 슈퍼로봇대전"),
    ("s3", 89664, 78, 24, "슈퍼로봇대전 EX"),
    ("s4", 91600, 92, 24, "트레이닝 모드"),
]
# 굵은 폰트(HANDotumB/malgunbd)는 이 크기에서 속공간이 막혀 뭉갠다.
# 레귤러 HANDotum 을 stroke_width 1 로 부풀리는 쪽이 훨씬 또렷하다.
FONT = "C:/Windows/Fonts/HANDotum.ttf"
FONT_FALLBACK = "C:/Windows/Fonts/malgun.ttf"
SHEAR = 0.18       # 원본 이탤릭 기울기에 맞춘다


def read_strip(data, off, wb, rows):
    out = []
    for y in range(rows):
        row = data[off + y * wb: off + y * wb + wb]
        r = []
        for b in row:
            r.append(b & 0xF); r.append(b >> 4)
        out.append(r)
    return out


def write_strip(data, off, wb, px):
    for y, row in enumerate(px):
        buf = bytearray(wb)
        for x in range(0, len(row), 2):
            buf[x // 2] = (row[x] & 0xF) | ((row[x + 1] & 0xF) << 4)
        data[off + y * wb: off + y * wb + wb] = buf


def text_band(px):
    """글자를 앉힐 행 범위. 원본 네 스트립은 모두 24행 블록의 4~23행을 쓴다
    ('트레이닝 모드'만 밑선이 없어 22행에서 끝날 뿐이다). 항목마다 글자 크기가
    달라지면 보기 나쁘므로 네 개 모두 같은 밴드를 쓴다."""
    rows = [y for y, r in enumerate(px) if any(v != BG for v in r)]
    if not rows:
        return (0, len(px) - 1)
    return (rows[0], max(rows[-1], len(px) - 1))


def _mask(text, w, h, font_path, shear, stroke=1):
    """주어진 칸에 최대한 크게 채운 굵은 이탤릭 한글 마스크.

    한글은 획이 가늘어 그냥 그리면 침식 깊이가 1에서 끝나 '속 빈 윤곽선'이 된다.
    stroke_width 로 획을 부풀려 최소 3px 을 만들어야 원본처럼 흰 코어가 생긴다.
    """
    for size in range(h + 8, 6, -1):
        try:
            f = ImageFont.truetype(font_path, size)
        except OSError:
            return None, 0
        tmp = Image.new("L", (w * 3, h * 4), 0)
        ImageDraw.Draw(tmp).text((14, 8), text, font=f, fill=255,
                                 stroke_width=stroke, stroke_fill=255)
        bb = tmp.getbbox()
        if bb is None:
            continue
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw + int(th * shear) <= w - 2 and th <= h:
            crop = tmp.crop(bb)
            sh = crop.transform((tw + int(th * shear), th), Image.AFFINE,
                                (1, shear, -shear * th, 0, 1, 0), resample=Image.BILINEAR)
            return sh.point(lambda v: 255 if v > 100 else 0), size
    return None, 0


def build(text, w, h, band):
    """(픽셀 2차원 배열, 폰트크기). band=(top,bottom) 원본 글자 행 범위."""
    top, bot = band
    bh = bot - top + 1
    m = size = None
    for fp in (FONT, FONT_FALLBACK):
        m, size = _mask(text, w, bh, fp, SHEAR)
        if m is not None:
            break
    if m is None:
        raise ValueError(f"'{text}' 를 {w}x{bh} 안에 못 넣음")

    canvas = Image.new("L", (w, h), 0)
    canvas.paste(m, ((w - m.width) // 2, top + (bh - m.height) // 2))
    mp = canvas.load()
    on = lambda x, y: 0 <= x < w and 0 <= y < h and mp[x, y] > 128

    px = [[BG] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if not on(x, y):
                continue
            # 침식 깊이 (3까지만 구분하면 충분하다)
            d = 3
            for r in (1, 2):
                ring = [(x + dx, y + dy) for dy in range(-r, r + 1) for dx in range(-r, r + 1)]
                if not all(on(a, b) for a, b in ring):
                    d = r; break
            if d == 1:
                # 배경이 우하단 쪽이면 그늘, 아니면 밝은 테두리
                shade = (not on(x + 1, y)) or (not on(x, y + 1)) or (not on(x + 1, y + 1))
                px[y][x] = RIM_SHADE if shade else RIM_LIT
            elif d == 2:
                px[y][x] = MID
            else:
                px[y][x] = CORE
    return px, size
