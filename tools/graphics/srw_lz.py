# -*- coding: utf-8 -*-
"""SRWCB 그래픽 압축(LZ77 계열) 디코더 — SLPS_020.70 RAM 0x8004e548 역분석.

포맷
  * 플래그 비트열: 바이트 단위로 채우고 MSB 부터 소비.
  * 비트 1        -> 리터럴 1바이트
  * 비트 0 + 1    -> 롱 매치: 빅엔디안 16비트 워드
                      offset = (w >> 3) - 0x2000      (-8192 ~ -1)
                      len3   = w & 7
                      len3!=0 -> length = len3 + 2    (3~9)
                      len3==0 -> 다음 1바이트 L; L==0 이면 스트림 종료,
                                 아니면 length = L + 1 (2~256)
  * 비트 0 + 0    -> 숏 매치: 플래그 비트 2개로 code(0~3),
                      다음 1바이트 b -> offset = b - 0x100 (-256 ~ -1)
                      length = code + 2 (2~5)

원본은 플래그 바이트가 0xFF 일 때 8리터럴 고속 경로를 타지만 결과는 동일하다.
"""


def decompress(src: bytes, pos: int = 0, limit: int | None = None) -> tuple[bytes, int]:
    """(해제 결과, 소비한 소스 길이) 반환."""
    out = bytearray()
    bitbuf = 0          # $a3 (bit 8 이 다음 플래그 비트)
    counter = 0x80      # $t0

    def bit() -> int:
        nonlocal bitbuf, counter, pos
        counter <<= 1
        if counter & 0x100:
            counter = 1
            bitbuf = src[pos]; pos += 1
        bitbuf = (bitbuf << 1) & 0x1FF
        return (bitbuf >> 8) & 1

    while True:
        if bit():                                   # 리터럴
            out.append(src[pos]); pos += 1
        elif bit():                                 # 롱 매치
            w = (src[pos] << 8) | src[pos + 1]; pos += 2
            disp = (w >> 3) - 0x2000
            n = w & 7
            if n:
                n += 2
            else:
                ln = src[pos]; pos += 1
                if ln == 0:
                    break                           # 종료
                n = ln + 1
            s = len(out) + disp
            for _ in range(n):
                out.append(out[s]); s += 1
        else:                                       # 숏 매치
            code = (bit() << 1) | bit()
            disp = src[pos] - 0x100; pos += 1
            n = code + 2
            s = len(out) + disp
            for _ in range(n):
                out.append(out[s]); s += 1
        if limit is not None and len(out) > limit:
            raise ValueError(f"출력 초과 {len(out)} > {limit}")
    return bytes(out), pos


def _table(data: bytes) -> list[int]:
    import struct
    n = struct.unpack_from("<I", data, 0)[0] // 4          # 첫 값 = 표 크기 = 첫 멤버 오프셋
    return [struct.unpack_from("<I", data, 4 * i)[0] for i in range(n)]


def archive_members(data: bytes, style: str = "auto") -> list[tuple[int, int]]:
    """선두 u32 표에서 (start, end) 목록.

    C_SMAP.BIN 계열('skew'): 표는 [a0,b0,a1,b1,...] 이고 멤버 i 의 실제 위치는
        start_i = a_i + 8*i,  end_i = b_i + 8*i + 4  (= start_{i+1})
    로 멤버마다 8바이트씩 밀린다. C_SMAP 293개 전부 소비 길이가 정확히 일치함을 확인.

    EFFECT.BIN / F_BBACK.BIN 계열('plain'): 표가 그대로 오프셋이라 순차로 이어진다.
    """
    tbl = _table(data)
    if style in ("auto", "skew"):
        out = []
        for i in range(len(tbl) // 2):
            s = tbl[2 * i] + 8 * i
            e = tbl[2 * i + 1] + 8 * i + 4
            if 0 < s < e <= len(data):
                out.append((s, e))
        if style == "skew" or (out and _probe(data, out[0])):
            return out
    return sequential_members(data, tbl[0])


def _probe(data: bytes, se: tuple[int, int]) -> bool:
    s, e = se
    try:
        _, used = decompress(data[s:e], 0, limit=4 * 1024 * 1024)
        return used == e - s
    except Exception:
        return False


def sequential_members(data: bytes, start: int, align_search: int = 16,
                       max_members: int = 4096) -> list[tuple[int, int]]:
    """표 규칙을 모르는 파일용 — 앞에서부터 스트림을 이어서 찾아 나간다."""
    pos, out, miss = start, [], 0
    while pos < len(data) - 16 and len(out) < max_members:
        hit = None
        for al in range(align_search):
            try:
                _, used = decompress(data[pos + al:], 0, limit=4 * 1024 * 1024)
                if used > 64:
                    hit = (pos + al, pos + al + used); break
            except Exception:
                pass
        if hit is None:
            miss += 1
            if miss > 2: break
            pos += 4; continue
        miss = 0; out.append(hit); pos = hit[1]
    return out
