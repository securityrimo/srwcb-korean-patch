# -*- coding: utf-8 -*-
"""v0.10.1 CB 이미지의 C_SMAP.BIN 을 한글 메뉴판으로 제자리 교체한다.

새 C_SMAP 은 원본과 크기가 같으므로 원래 LBA 2081 에 그대로 덮어쓴다.
(파일을 옮기면 뒤 멤버 오프셋이 밀려 타이틀 로고·메뉴 창이 사라진다 — 실측 확인)
"""
import math, os, shutil, sys, hashlib

sys.path.insert(0, "D:/ps1/roms/SRWCB/korean_patch/tools")
from patch_raw_track_exes import SECTOR_SIZE, USER_DATA_OFFSET as UDO, USER_DATA_SIZE as UDS, rebuild_mode2_form1

SP = os.path.dirname(os.path.abspath(__file__))
BASE = "D:/ps1/roms/SRWCB/korean_patch/test_build/third_full/Super Robot Taisen Complete Box Korean v0.10.1 (Track 1).bin"
OUT = "D:/ps1/roms/SRWCB/korean_patch/test_build/third_full/Super Robot Taisen Complete Box Korean v0.10.2 (Track 1).bin"
NEW = f"{SP}/gfx/C_SMAP_ko.BIN"
LBA, SIZE = 2081, 9932026


def main():
    payload = open(NEW, "rb").read()
    assert len(payload) == SIZE, f"크기 {len(payload)} != {SIZE}"
    if os.path.exists(OUT): os.remove(OUT)
    shutil.copyfile(BASE, OUT)
    cnt = math.ceil(len(payload) / UDS)
    changed = 0
    with open(OUT, "r+b") as t:
        for i in range(cnt):
            t.seek((LBA + i) * SECTOR_SIZE)
            sec = bytearray(t.read(SECTOR_SIZE))
            chunk = payload[i * UDS:(i + 1) * UDS]
            if sec[UDO:UDO + len(chunk)] == chunk:
                continue
            sec[UDO:UDO + len(chunk)] = chunk
            rebuild_mode2_form1(sec)
            t.seek((LBA + i) * SECTOR_SIZE); t.write(sec)
            changed += 1
    print(f"C_SMAP 제자리 교체: {cnt} 섹터 중 {changed} 섹터 갱신 (LBA {LBA})")
    h = hashlib.sha256()
    with open(OUT, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    print("OUT", OUT)
    print("크기", os.path.getsize(OUT), " sha", h.hexdigest()[:16])


if __name__ == "__main__":
    main()
