# -*- coding: utf-8 -*-
"""
扫描 Kindle 上的 azw3 / azw / mobi，判定：
  - 压缩方式、加密方式（只做识别，不涉及解密）
  - 是 MOBI6 还是 KF8(azw3)
  - 是否含 EXTH 1004 (DRM) 记录
用法: python scan_ebooks.py <目录>
"""
import os
import struct
import sys
import json

SRC = sys.argv[1] if len(sys.argv) > 1 else "F:/documents"
EXT = (".azw3", ".azw", ".mobi", ".prc")
WORKROOT = os.environ.get("KINDLE_JB_WORK") or os.path.join(os.getcwd(), "kindle_work")
os.makedirs(WORKROOT, exist_ok=True)

def analyze(path):
    with open(path, "rb") as f:
        head = f.read(1 << 16)
    size = os.path.getsize(path)
    if len(head) < 100 or head[60:68] != b"BOOKMOBI":
        return {"type": "坏文件/非 MOBI", "enc": None}
    nrec = struct.unpack(">H", head[76:78])[0]
    off0 = struct.unpack(">L", head[78:82])[0]
    if off0 + 16 > len(head):
        return {"type": "头部异常", "enc": None}
    comp, _, tlen, rc, rs, enc = struct.unpack(">HHIHHH", head[off0:off0 + 14])
    mh = off0 + 16
    if head[mh:mh + 4] != b"MOBI":
        return {"type": "无 MOBI 头", "enc": enc}
    hlen = struct.unpack(">L", head[mh + 4:mh + 8])[0]
    ver = struct.unpack(">L", head[mh + 20:mh + 24])[0]
    # EXTH 区域
    exth = mh + hlen
    has1004 = False
    if head[exth:exth + 4] == b"EXTH":
        elen, ecount = struct.unpack(">LL", head[exth + 4:exth + 12])
        p = exth + 12
        for _ in range(ecount):
            if p + 8 > len(head):
                break
            rtype, rlen = struct.unpack(">LL", head[p:p + 8])
            if rtype == 1004:
                has1004 = True
            p += rlen
            if rlen <= 0:
                break
    kind = {1: "无压缩", 2: "PalmDOC", 17480: "HUFF/CDIC"}.get(comp, str(comp))
    fmt = "MOBI6/KF7" if ver <= 6 else ("KF8 (azw3)" if ver == 8 else f"版本 {ver}")
    return {
        "type": fmt, "enc": enc, "has1004": has1004,
        "compress": kind, "size": size, "records": nrec, "textlen": tlen,
    }

rows = []
for fn in sorted(os.listdir(SRC)):
    if not fn.lower().endswith(EXT):
        continue
    p = os.path.join(SRC, fn)
    if not os.path.isfile(p):
        continue
    try:
        r = analyze(p)
    except Exception as e:
        r = {"type": f"异常 {e}", "enc": None}
    r["file"] = fn
    rows.append(r)

clean, drm, bad = [], [], []
for r in rows:
    if r.get("enc") == 0 and not r.get("has1004"):
        clean.append(r)
    elif r.get("enc") is None:
        bad.append(r)
    else:
        drm.append(r)

print(f"扫描目录: {SRC}")
print(f"共 {len(rows)} 本：无 DRM {len(clean)} / 带 DRM {len(drm)} / 异常 {len(bad)}")
print()
print("===== A. 无加密，可直接转换 =====")
for r in clean:
    print(f'  {r["file"][:56]:58s} {r["type"]:12s} {r["size"]/1048576:7.2f}MB')
print()
print("===== B. 带 DRM（无法转换）=====")
for r in drm:
    print(f'  {r["file"][:56]:58s} enc={r["enc"]} 1004={r["has1004"]}  {r["size"]/1048576:7.2f}MB')
if bad:
    print()
    print("===== C. 异常/损坏 =====")
    for r in bad:
        print(f'  {r["file"][:56]:58s} {r["type"]}')

with open(os.path.join(WORKROOT, "_ebook_scan.json"), "w", encoding="utf-8") as f:
    json.dump({"clean": clean, "drm": drm, "bad": bad}, f, ensure_ascii=False, indent=1)
print()
print(f"明细已存 {os.path.join(WORKROOT, '_ebook_scan.json')}")
