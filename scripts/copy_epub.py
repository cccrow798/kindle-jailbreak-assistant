# -*- coding: utf-8 -*-
"""
把转换好的 EPUB 拷入 Kindle 的 documents 目录（KOReader 首页即此目录）。
- **只拷贝台账 _converted_ok.json 里登记且体积吻合的文件**：
  未通过校验的产物（例如历史上被污染的膨胀文件）绝不会被拷进设备
- 只创建新文件，不覆盖、不删除设备上任何已有书籍
- 逐文件校验大小 + MD5
- 可重复运行：已一致的文件自动跳过

用法:
    python copy_epub.py --drive F:                       # 推荐（源/台账走工作目录）
    python copy_epub.py --source ./epub_out --drive F: --sub documents
    python copy_epub.py [源目录] [目标盘符] [目标子目录]   # 兼容旧的位置参数写法
     默认: source=<工作目录>/epub_out  target=<盘>:/documents
"""
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKROOT = os.environ.get("KINDLE_JB_WORK") or os.path.join(os.getcwd(), "kindle_work")


def _args():
    a = sys.argv[1:]
    src = drive = sub = None
    pos = []
    i = 0
    while i < len(a):
        if a[i] in ("--source", "--src") and i + 1 < len(a):
            src = a[i + 1]; i += 2; continue
        if a[i] in ("--drive", "--dest") and i + 1 < len(a):
            drive = a[i + 1]; i += 2; continue
        if a[i] == "--sub" and i + 1 < len(a):
            sub = a[i + 1]; i += 2; continue
        pos.append(a[i]); i += 1
    if src is None and pos:
        src = pos[0]
    if drive is None and len(pos) > 1:
        drive = pos[1]
    if sub is None and len(pos) > 2:
        sub = pos[2]
    return src, drive, sub


SRC_A, DRIVE_A, SUB_A = _args()
SRC = SRC_A or os.path.join(WORKROOT, "epub_out")
DRIVE = (DRIVE_A or "F:").rstrip("\\/")
SUB = SUB_A or "documents"
DST = os.path.join(DRIVE + os.sep, SUB)
LEDGER = os.path.join(WORKROOT, "_converted_ok.json")


def md5(p, chunk=1 << 20):
    h = hashlib.md5()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    if not os.path.isdir(SRC):
        print(f"源目录不存在: {SRC}")
        return 1
    if not os.path.isdir(DRIVE + os.sep):
        print(f"设备未挂载: {DRIVE}")
        return 1
    os.makedirs(DST, exist_ok=True)
    try:
        with open(LEDGER, encoding="utf-8") as f:
            ledger = json.load(f)
    except Exception as e:
        print(f"读不到台账 {LEDGER}: {e}")
        return 1
    all_files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".epub"))
    files, excluded = [], []
    for fn in all_files:
        stem = os.path.splitext(fn)[0]
        rec = ledger.get(stem)
        p = os.path.join(SRC, fn)
        if rec and os.path.getsize(p) == rec.get("size"):
            files.append(fn)
        else:
            excluded.append(fn)
    print(f"台账登记 {len(ledger)} 本；本次拷入 {len(files)} 本 → {DST}")
    if excluded:
        print(f"⚠ 未通过校验、已排除 {len(excluded)} 个（不会拷入设备）：")
        for fn in excluded:
            print(f"    - {fn[:64]}  {os.path.getsize(os.path.join(SRC, fn))/1048576:.1f} MB")
    ok = skip = fail = 0
    fails = []
    for i, fn in enumerate(files, 1):
        s = os.path.join(SRC, fn)
        d = os.path.join(DST, fn)
        ss = os.path.getsize(s)
        tag = f"[{i}/{len(files)}] {fn[:44]}"
        if os.path.isfile(d) and os.path.getsize(d) == ss and md5(s) == md5(d):
            print(f"  = {tag}  已一致，跳过")
            skip += 1
            continue
        if os.path.isfile(d):
            print(f"  ! {tag}  目标已存在同名文件（内容不同），跳过不覆盖")
            fails.append((fn, "目标同名文件已存在"))
            fail += 1
            continue
        try:
            shutil.copyfile(s, d)
            if os.path.getsize(d) != ss:
                raise IOError(f"大小不符 {os.path.getsize(d)} != {ss}")
            if md5(s) != md5(d):
                raise IOError("MD5 不符")
            print(f"  + {tag}  {ss/1048576:.2f} MB")
            ok += 1
        except Exception as e:
            print(f"  ! {tag}  失败: {e}")
            fails.append((fn, str(e)))
            fail += 1
    print()
    print(f"完成：写入 {ok} / 已一致 {skip} / 失败 {fail}")
    if fails:
        print("失败清单：")
        for n, why in fails:
            print(f"  - {n}: {why}")
    import shutil as _sh
    u = _sh.disk_usage(DRIVE + os.sep)
    print(f"设备剩余空间: {u.free/2**30:.2f} GB")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
