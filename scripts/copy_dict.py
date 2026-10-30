# -*- coding: utf-8 -*-
r"""
把 StarDict 词典拷入 Kindle 的 KOReader 词典目录（含 res/ 图片子目录）。
源: <源目录>/<词典名>/{*.ifo,*.idx,*.dict.dz,*.syn,res/*}
目标: <Kindle盘>:\koreader\data\dict\<词典名>\

用法:
    python copy_dict.py --drive F: --source ./dict          # 推荐
    python copy_dict.py --source ./dict --wait 30           # 等设备挂载最多 30 秒
    python copy_dict.py [等待秒数] [源目录]                  # 兼容旧的位置参数写法
"""
import hashlib
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EXT_OK = (".ifo", ".idx", ".dict.dz", ".syn", ".dict", ".css", ".lua")


def _args():
    a = sys.argv[1:]
    drive, wait, source = None, 0, None
    i = 0
    while i < len(a):
        if a[i] == "--drive" and i + 1 < len(a):
            drive = a[i + 1]; i += 2; continue
        if a[i] == "--source" and i + 1 < len(a):
            source = a[i + 1]; i += 2; continue
        if a[i] == "--wait" and i + 1 < len(a):
            wait = int(a[i + 1]); i += 2; continue
        if a[i].isdigit() and wait == 0:
            wait = int(a[i]); i += 1; continue
        if source is None:
            source = a[i]; i += 1; continue
        i += 1
    return drive, wait, source


DRIVE_ARG, WAIT, SRC_ARG = _args()
SRC_ROOT = SRC_ARG if SRC_ARG else os.path.join(HERE, "dict")
if DRIVE_ARG:
    DRIVE_ARG = DRIVE_ARG.rstrip("\\/") + os.sep


def md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def find_kindle():
    """扫描盘符，找带 system/version.txt 的 Kindle 分区"""
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        if not os.path.isdir(root):
            continue
        if os.path.isfile(os.path.join(root, "system", "version.txt")):
            return root
    return None


def main():
    # 1) 等设备
    deadline = time.time() + WAIT
    if DRIVE_ARG:
        root = DRIVE_ARG if os.path.isdir(DRIVE_ARG) else None
        if root is None:
            print(f"[等待中] 盘符 {DRIVE_ARG} 暂不可用")
    else:
        root = find_kindle()
    while root is None and WAIT > 0 and time.time() < deadline:
        time.sleep(4)
        root = DRIVE_ARG if DRIVE_ARG and os.path.isdir(DRIVE_ARG) else find_kindle()
    if root is None:
        print("[等待中] 未检测到 Kindle（需含 system/version.txt 的可移动盘）")
        return 2

    ver = ""
    try:
        with open(os.path.join(root, "system", "version.txt"), "r", errors="ignore") as f:
            ver = f.read().strip()
    except Exception:
        pass
    print(f"[设备] {root}  固件 {ver}")

    if not os.path.isdir(os.path.join(root, "koreader")):
        print("[中止] 该盘没有 koreader 目录，确认是不是 Kindle 分区")
        return 3

    dst_root = os.path.join(root, "koreader", "data", "dict")
    os.makedirs(dst_root, exist_ok=True)

    names = sorted(d for d in os.listdir(SRC_ROOT) if os.path.isdir(os.path.join(SRC_ROOT, d)))
    ok = skip = fail = 0
    for name in names:
        sdir = os.path.join(SRC_ROOT, name)
        ddir = os.path.join(dst_root, name)
        os.makedirs(ddir, exist_ok=True)
        # 顶层词典文件 + res/ 图片资源（KOReader readerdictionary.lua 会读 dict_path/res）
        tasks = []
        for fn in sorted(os.listdir(sdir)):
            sp = os.path.join(sdir, fn)
            if os.path.isfile(sp) and fn.lower().endswith(EXT_OK):
                tasks.append((fn, sp, os.path.join(ddir, fn)))
            elif os.path.isdir(sp) and fn == "res":
                os.makedirs(os.path.join(ddir, "res"), exist_ok=True)
                for rf in sorted(os.listdir(sp)):
                    if os.path.isfile(os.path.join(sp, rf)):
                        tasks.append((f"res/{rf}", os.path.join(sp, rf),
                                      os.path.join(ddir, "res", rf)))
        print(f"\n== {name}  ({len(tasks)} 个文件)")
        for fn, s, d in tasks:
            ss = os.path.getsize(s)
            if os.path.isfile(d) and os.path.getsize(d) == ss and md5(s) == md5(d):
                print(f"   = 已存在且一致  {fn}")
                skip += 1
                continue
            try:
                if os.path.isfile(d):
                    os.remove(d)
                shutil.copyfile(s, d)   # 直接写目标名（Kindle FAT 上 os.replace 会被拒）
                if os.path.getsize(d) != ss:
                    raise IOError(f"大小不符 {os.path.getsize(d)}!={ss}")
                t, u = md5(s), md5(d)
                if t != u:
                    raise IOError(f"MD5 不符 {t[:8]}!={u[:8]}")
                print(f"   + 已写入  {fn}  {ss/1048576:.2f} MB")
                ok += 1
            except Exception as e:
                print(f"   ! 失败  {fn}  {e}")
                fail += 1

    print(f"\n[结果] 新写入 {ok} / 跳过 {skip} / 失败 {fail}")
    print(f"[目录] {dst_root}")
    if fail == 0:
        print("[下一步] 安全弹出后，重启 KOReader → 搜索 → 设置 → 词典设置 中勾选即可")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
