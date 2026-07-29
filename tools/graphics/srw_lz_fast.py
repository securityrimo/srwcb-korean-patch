# -*- coding: utf-8 -*-
"""srw_lz.decompress 의 고속판 (동작 동일, 인라인 비트리더 + 슬라이스 복사)."""
def decompress(src, pos=0):
    out = bytearray(); ext = out.extend; app = out.append
    bb = 0; ctr = 0x80
    n_src = len(src)
    while True:
        ctr <<= 1
        if ctr & 0x100:
            ctr = 1; bb = src[pos]; pos += 1
        bb = (bb << 1) & 0x1FF
        if bb & 0x100:                      # 리터럴
            app(src[pos]); pos += 1
            continue
        ctr <<= 1
        if ctr & 0x100:
            ctr = 1; bb = src[pos]; pos += 1
        bb = (bb << 1) & 0x1FF
        if bb & 0x100:                      # 롱 매치
            w = (src[pos] << 8) | src[pos + 1]; pos += 2
            disp = (w >> 3) - 0x2000
            n = w & 7
            if n:
                n += 2
            else:
                L = src[pos]; pos += 1
                if L == 0: break
                n = L + 1
        else:                               # 숏 매치
            ctr <<= 1
            if ctr & 0x100:
                ctr = 1; bb = src[pos]; pos += 1
            bb = (bb << 1) & 0x1FF
            c = 2 if (bb & 0x100) else 0
            ctr <<= 1
            if ctr & 0x100:
                ctr = 1; bb = src[pos]; pos += 1
            bb = (bb << 1) & 0x1FF
            if bb & 0x100: c |= 1
            disp = src[pos] - 0x100; pos += 1
            n = c + 2
        s = len(out) + disp
        if s < 0: raise IndexError("back-reference before start")
        if disp + n <= 0:                   # 비중첩 -> 슬라이스
            ext(out[s:s + n])
        else:
            for _ in range(n):
                app(out[s]); s += 1
    return bytes(out), pos
