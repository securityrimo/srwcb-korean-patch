# -*- coding: utf-8 -*-
"""C_SMAP.BIN 을 한글 게임 선택 메뉴가 든 버전으로 재구성한다 (크기·오프셋 완전 보존).

멤버 21 을 풀어 스트립 4개(제2차/제3차/EX/트레이닝 모드)를 한글로 다시 그리고
같은 코덱으로 재압축한다. 재압축 결과가 원본 멤버보다 작으므로 **원래 바이트 범위
안에** 넣고 남는 꼬리는 원본 바이트를 그대로 둔다(디코더는 종료 마커에서 멈춘다).

이렇게 하면 표도 파일 크기도 다른 멤버의 위치도 전부 그대로다. 처음엔 멤버가
127바이트 커져 뒤 멤버가 전부 밀렸고, 그 결과 타이틀 로고와 메뉴 창이 사라졌다.
"""
import struct, sys, os
SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SP)
from srw_lz_fast import decompress
from srw_lz_enc import compress
import menu_strips as M

SRC = "D:/ps1/roms/SRWCB/korean_patch/extracted/C_SMAP.BIN"
OUT = f"{SP}/gfx/C_SMAP_ko.BIN"
TARGET = 21


def members(d):
    n = struct.unpack_from("<I", d, 0)[0] // 4
    t = [struct.unpack_from("<I", d, 4 * i)[0] for i in range(n)]
    return n, [(t[2 * i] + 8 * i, t[2 * i + 1] + 8 * i + 4) for i in range(n // 2)]


def main():
    d = open(SRC, "rb").read()
    n, ms = members(d)
    s, e = ms[TARGET]
    raw, used = decompress(d[s:e], 0)
    assert used == e - s, "멤버21 소비 길이 불일치"
    body = bytearray(raw)

    for name, off, wb, rows, ko in M.STRIPS:
        src = M.read_strip(body, off, wb, rows)
        grad = M.row_gradient(src)
        px, size = M.build(ko, wb * 2, rows, grad)
        M.write_strip(body, off, wb, px)
        print(f"  {name} @{off} {wb*2}x{rows} <- '{ko}' ({size}px)")

    new = compress(bytes(body))
    room = e - s
    assert len(new) <= room, f"재압축 {len(new)} > 원본 {room} — 자리 부족"
    chk, u2 = decompress(new, 0)
    assert chk == bytes(body) and u2 == len(new), "재압축 왕복 실패"
    print(f"  멤버21 재압축 {room:,} -> {len(new):,} (여유 {room-len(new):,}B, 자리 그대로)")

    out = bytearray(d)
    out[s:s + len(new)] = new          # 남는 꼬리는 원본 바이트 유지
    outb = bytes(out)
    assert len(outb) == len(d), "파일 크기 변동"
    os.makedirs(f"{SP}/gfx", exist_ok=True)
    open(OUT, "wb").write(outb)

    # 검증 ① 표·다른 멤버 바이트가 전부 그대로
    n2, ms2 = members(outb)
    assert n2 == n and ms2 == ms, "표가 바뀜"
    for i, (a, b) in enumerate(ms):
        if i == TARGET: continue
        assert outb[a:b] == d[a:b], f"멤버 {i} 변경됨"
    # 검증 ② 대상 멤버가 패치된 픽셀로 해제되고, 소비 길이가 원본 범위 안
    o2, u3 = decompress(outb[s:e], 0)
    assert o2 == bytes(body) and u3 == len(new) <= room
    print(f"  검증 통과: 파일 {len(outb):,}B (원본과 동일), 멤버 {len(ms)}개 위치 불변")
    print(f"WROTE {OUT}")


if __name__ == "__main__":
    main()
