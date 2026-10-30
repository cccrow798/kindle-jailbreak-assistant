# -*- coding: utf-8 -*-
"""
独立复核：设备上的 EPUB 是否与电脑端产物一致且可正常打开
- 逐一比对：存在性、字节数、MD5、zip 结构（mimetype）
- 列出设备上不在台账内的 EPUB（可能是历史遗留/截断文件）
用法:
    python verify_epub.py --drive F:                 # 推荐
    python verify_epub.py --source ./epub_out --drive F:
    python verify_epub.py [源目录] [盘符]            # 兼容旧的位置参数写法
"""
import hashlib
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
WORKROOT = os.environ.get("KINDLE_JB_WORK") or os.path.join(os.getcwd(), "kindle_work")


def _args():
    a = sys.argv[1:]
    src = drive = None
    pos = []
    i = 0
    while i < len(a):
        if a[i] in ("--source", "--src") and i + 1 < len(a):
            src = a[i + 1]; i += 2; continue
        if a[i] in ("--drive", "--dest") and i + 1 < len(a):
            drive = a[i + 1]; i += 2; continue
        pos.append(a[i]); i += 1
    if src is None and pos:
        src = pos[0]
    if drive is None and len(pos) > 1:
        drive = pos[1]
    return src, drive


SRC_A, DRIVE_A = _args()
SRC = SRC_A or os.path.join(WORKROOT, "epub_out")
DRIVE = (DRIVE_A or "F:").rstrip("\\/")
DST = os.path.join(DRIVE + os.sep, "documents")
LEDGER = os.path.join(WORKROOT, "_converted_ok.json")


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def zip_ok(p):
    try:
        if not zipfile.is_zipfile(p):
            return False, "不是 zip"
        z = zipfile.ZipFile(p)
        if "mimetype" not in z.namelist():
            return False, "缺 mimetype"
        return True, ""
    except Exception as e:
        return False, str(e)


with open(LEDGER, encoding="utf-8") as f:
    ledger = json.load(f)

ok = bad = 0
problems = []
for stem, rec in sorted(ledger.items()):
    fn = stem + ".epub"
    s, d = os.path.join(SRC, fn), os.path.join(DST, fn)
    if not os.path.isfile(d):
        problems.append(f"{fn[:56]:58s} 设备上缺失")
        bad += 1
        continue
    ds = os.path.getsize(d)
    if ds != rec["size"]:
        problems.append(f"{fn[:56]:58s} 大小不符 设备 {ds} / 台账 {rec['size']}")
        bad += 1
        continue
    ms, md = md5(s), md5(d)
    if ms != md:
        problems.append(f"{fn[:56]:58s} MD5 不符")
        bad += 1
        continue
    good, why = zip_ok(d)
    if not good:
        problems.append(f"{fn[:56]:58s} 结构异常: {why}")
        bad += 1
        continue
    ok += 1

print(f"台账 {len(ledger)} 本：复核通过 {ok} / 异常 {bad}")
if problems:
    print("异常清单：")
    for p in problems:
        print("  ! " + p)

known = {stem + ".epub" for stem in ledger}
extra = []
if os.path.isdir(DST):
    for fn in sorted(os.listdir(DST)):
        if fn.lower().endswith(".epub") and fn not in known:
            p = os.path.join(DST, fn)
            g, why = zip_ok(p)
            extra.append((fn, os.path.getsize(p), g, why))
print()
print(f"设备上不在台账内的 EPUB：{len(extra)} 个")
for fn, sz, g, why in extra:
    flag = "正常" if g else f"异常({why})"
    print(f"  - {fn[:60]:62s} {sz/1048576:7.2f} MB  {flag}")

tot = sum(rec["size"] for rec in ledger.values())
print()
print(f"本轮写入设备合计 {tot/1048576:.0f} MB")
u = __import__("shutil").disk_usage(DRIVE + os.sep)
print(f"设备剩余空间 {u.free/2**30:.2f} GB")
