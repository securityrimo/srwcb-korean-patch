# -*- coding: utf-8 -*-
"""CB 부팅 '게임 선택' 메뉴 스트립 4개를 한글로 다시 그린다.

원본은 C_SMAP.BIN 멤버 21(해제 132,176B) 안의 4bpp 인덱스 비트맵이다.
스트립마다 stride(=행당 바이트)와 시작 오프셋이 다르고 배경 인덱스는 12.
글자는 검은 외곽선(0) + 행마다 달라지는 세로 그라데이션 채움으로 그려져 있다.
같은 규칙으로 한글을 그려 넣어 원본 크기·바이트 수를 그대로 유지한다.
"""
from PIL import Image, ImageDraw, ImageFont

BG = 12
OUTLINE = 0

# 멤버 21 은 표준 TIM 들이 줄줄이 붙어 있는 덩어리다. 메뉴 항목 4개는 4bpp TIM 이고
# 픽셀 블록의 위치·크기는 TIM 헤더가 정확히 알려 준다(추측 금지).
#
#   [2] @85056 184x24 VRAM(320, 80)  픽셀 85120~87328   제2차
#   [3] @87328 184x24 VRAM(320,104)  픽셀 87392~89600   제3차
#   [4] @89600 156x24 VRAM(320,128)  픽셀 89664~91536   EX
#   [5] @91536 184x24 VRAM(320,  0)  픽셀 91600~93808   트레이닝 모드
#
# 이 범위를 한 바이트라도 넘기면 **다음 TIM 의 헤더**를 부수고, 그러면 그 뒤의
# 메뉴 창·화살표·타이틀 로고가 통째로 안 나온다(실제로 그렇게 됐었다).
#
# (이름, 픽셀 시작 오프셋, stride 바이트, 행 수, 한국어)
STRIPS = [
    ("s1", 85120, 92, 24, "제2차 슈퍼로봇대전"),
    ("s2", 87392, 92, 24, "제3차 슈퍼로봇대전"),
    ("s3", 89664, 78, 24, "슈퍼로봇대전 EX"),
    ("s4", 91600, 92, 24, "트레이닝 모드"),
]
FONT = "C:/Windows/Fonts/malgunbd.ttf"


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


def row_gradient(px):
    """행마다 '외곽선도 배경도 아닌' 인덱스의 최빈값 = 채움색."""
    from collections import Counter
    grad = []
    for row in px:
        c = Counter(v for v in row if v not in (BG, OUTLINE))
        grad.append(c.most_common(1)[0][0] if c else 6)
    return grad


def text_mask(text, w, h, font_path=FONT, shear=0.22):
    """한글을 굵게 그려 이탤릭 기울기를 준 이진 마스크."""
    for size in range(h + 6, 6, -1):
        f = ImageFont.truetype(font_path, size)
        tmp = Image.new("L", (w * 3, h * 3), 0)
        d = ImageDraw.Draw(tmp)
        d.text((10, 5), text, font=f, fill=255)
        bb = tmp.getbbox()
        if bb is None:
            continue
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        # 기울인 뒤 외곽선 1px 이 들어갈 여유(가로세로 2px)
        if tw + int(th * shear) <= w - 4 and th <= h - 4:
            crop = tmp.crop(bb)
            sheared = crop.transform(
                (tw + int(th * shear), th), Image.AFFINE,
                (1, shear, -shear * th, 0, 1, 0), resample=Image.NEAREST)
            m = Image.new("L", (w, h), 0)
            m.paste(sheared, ((w - sheared.width) // 2, (h - th) // 2))
            return m, size
    raise ValueError(f"'{text}' 를 {w}x{h} 안에 못 넣음")


def build(text, w, h, grad):
    m, size = text_mask(text, w, h)
    mp = m.load()
    px = [[BG] * w for _ in range(h)]
    # 외곽선: 마스크를 8방향으로 1px 팽창한 뒤 원본을 뺀 영역
    for y in range(h):
        for x in range(w):
            if mp[x, y] > 128:
                continue
            near = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= xx < w and 0 <= yy < h and mp[xx, yy] > 128:
                        near = True; break
                if near: break
            if near:
                px[y][x] = OUTLINE
    for y in range(h):
        for x in range(w):
            if mp[x, y] > 128:
                px[y][x] = grad[y]
    return px, size
