#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kindle 设备识别（只读）。

输出：固件版本、架构推断、越狱状态、已装组件、词典、书籍统计、垃圾候选、剩余空间。

用法：
    python detect_kindle.py                 # 自动扫描盘符找 Kindle
    python detect_kindle.py F:              # 指定盘符
    python detect_kindle.py F: --serial G090KB1234567890   # 附带序列号 -> 推断机型
    python detect_kindle.py F: --json       # 机器可读输出

本脚本不做任何写入、删除、改名操作。
"""
import argparse
import json
import os
import re
import shutil
import sys

# 常见序列号前缀 -> (机型, KOReader 平台后缀)
MODEL_HINTS = [
    ("G090", ("Paperwhite 2 / Paperwhite 3（需配合固件与官方向导确认）", "kindlepw2")),
    ("G000T6", ("Paperwhite 4", "kindlehf")),
    ("G0011Q", ("Kindle 11 (2022)", "kindlehf")),
    ("G0016T", ("Scribe", "kindlehf")),
    ("G000", ("较早机型（Kindle 4/5/Touch/PW1 等）", "kindlepw2")),
]

JUNK_SUFFIX = (".kfx.sd", ".tmp.sa.decompressed")
BOOK_EXT = (".epub", ".azw3", ".azw", ".mobi", ".kfx", ".pdf", ".txt", ".cbz")

FIELDS = [
    # (相对路径, 说明)
    ("documents/JAILBROKEN.txt", "越狱标记文件"),
    ("libkh/bin/fbink", "越狱核心组件 fbink"),
    ("apps/tech.hackerdude.winterbreak", "WinterBreak2 运行环境"),
    ("mesquito", "WinterBreak2 运行环境"),
    ("kmc/kpm/kpm.db", "KPM 包管理数据库"),
    ("koreader/reader.lua", "KOReader 程序本体"),
    ("documents/KOReader.sh", "KOReader 图书馆入口 scriptlet"),
]


def find_kindle():
    """扫描盘符，找带 system/version.txt 的分区"""
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        try:
            if os.path.isfile(os.path.join(root, "system", "version.txt")):
                return root
        except OSError:
            continue
    return None


def sizeof(path):
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    total = 0
    for r, _, fs in os.walk(path):
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return total


def arch_of(firmware):
    """5.16.3 起为 hard-float，5.16.2.1.1 及以前为 soft-float"""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", firmware or "")
    if not m:
        return "未知"
    major, minor, patch = (int(x) for x in m.groups())
    if (major, minor, patch) >= (5, 16, 3):
        return "hard-float"
    return "soft-float"


def infer_platform(firmware):
    a = arch_of(firmware)
    if a == "hard-float":
        return "kindlehf"
    if a == "soft-float":
        return "kindlepw2"
    return "未知"


def scan_root(root):
    r = {"root": root, "exists": os.path.isdir(root)}
    if not r["exists"]:
        return r

    # 固件
    fw = ""
    vp = os.path.join(root, "system", "version.txt")
    if os.path.isfile(vp):
        try:
            with open(vp, "r", errors="ignore") as f:
                fw = f.read().strip()
        except OSError:
            pass
    r["firmware"] = fw or "未读到"
    r["arch"] = arch_of(fw)
    r["platform_suffix"] = infer_platform(fw)

    # 关键文件
    r["markers"] = {p: os.path.exists(os.path.join(root, p)) for p, _ in FIELDS}
    r["jailbroken"] = bool(r["markers"].get("libkh/bin/fbink"))

    # 待安装的系统更新（会顶掉可利用的固件版本）
    pending = []
    try:
        for n in os.listdir(root):
            low = n.lower()
            if (low.startswith("update") and low.endswith(".bin")) \
               or low.endswith("update.bin.tmp.partial"):
                pending.append(n)
    except OSError:
        pass
    r["pending_updates"] = pending

    # KPM 已装包
    pkgs = []
    pdir = os.path.join(root, "kmc", "kpm", "packages")
    if os.path.isdir(pdir):
        try:
            pkgs = sorted(d for d in os.listdir(pdir)
                          if os.path.isdir(os.path.join(pdir, d)))
        except OSError:
            pass
    r["kpm_packages"] = pkgs

    # KOReader 插件
    plugins = []
    pdir = os.path.join(root, "koreader", "plugins")
    if os.path.isdir(pdir):
        try:
            plugins = sorted(d for d in os.listdir(pdir)
                             if d.endswith(".koplugin"))
        except OSError:
            pass
    r["koreader_plugins"] = plugins

    # 词典
    dicts = []
    ddir = os.path.join(root, "koreader", "data", "dict")
    if os.path.isdir(ddir):
        for dirpath, _dirnames, filenames in os.walk(ddir):
            for fn in filenames:
                if fn.lower().endswith(".ifo"):
                    d = os.path.dirname(dirpath) if os.path.basename(dirpath) == "res" else dirpath
                    dicts.append({"ifo": os.path.join(dirpath, fn), "dir": d})
    r["dicts"] = dicts

    # 词典启用状态（全局 settings.reader.lua）
    disabled, order = [], []
    sp = os.path.join(root, "koreader", "settings.reader.lua")
    if os.path.isfile(sp):
        try:
            with open(sp, "rb") as f:
                t = f.read().decode("utf-8", "surrogateescape")
            m = re.search(r'\["dicts_disabled"\]\s*=\s*\{([^{}]*)\}', t)
            if m:
                disabled = re.findall(r'\["([^"]+)"\]\s*=\s*true', m.group(1))
            m = re.search(r'\["dicts_order"\]\s*=\s*\{([^{}]*)\}', t)
            if m:
                order = re.findall(r'\["([^"]+)"\]\s*=\s*\d+', m.group(1))
        except (OSError, re.error):
            pass
    r["dicts_disabled"] = disabled
    r["dicts_order"] = order

    # documents 统计
    doc = os.path.join(root, "documents")
    by_ext, sdr_total, sdr_empty, junk = {}, 0, 0, []
    if os.path.isdir(doc):
        try:
            for n in os.listdir(doc):
                p = os.path.join(doc, n)
                low = n.lower()
                if os.path.isdir(p):
                    if low.endswith(".sdr"):
                        sdr_total += 1
                        try:
                            if not os.listdir(p):
                                sdr_empty += 1
                        except OSError:
                            pass
                    continue
                if low.endswith(".kfx.sd") or low.endswith(".tmp.sa.decompressed") \
                   or n.startswith(".fuse_hidden") \
                   or (low.endswith(".tgz") and "crash" in low):
                    junk.append(p)
                    continue
                for e in BOOK_EXT:
                    if low.endswith(e):
                        by_ext[e] = by_ext.get(e, 0) + 1
                        break
        except OSError:
            pass
    r["documents"] = {
        "by_ext": by_ext,
        "sdr_total": sdr_total,
        "sdr_empty": sdr_empty,
        "junk_candidates": len(junk),
        "size_mb": round(sizeof(doc) / 1048576, 1) if os.path.isdir(doc) else 0,
    }

    # 空间
    try:
        u = shutil.disk_usage(root)
        r["free_gb"] = round(u.free / 2 ** 30, 2)
        r["total_gb"] = round(u.total / 2 ** 30, 2)
    except OSError:
        r["free_gb"] = None
        r["total_gb"] = None

    return r


def hint_model(serial):
    s = (serial or "").upper().strip()
    for pref, (model, plat) in MODEL_HINTS:
        if s.startswith(pref.upper()):
            return model, plat
    return None, None


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("drive", nargs="?", default=None)
    ap.add_argument("--serial", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = None
    if args.drive:
        root = args.drive.rstrip("\\/") + os.sep
        if not os.path.isdir(root):
            print(f"!! 找不到目录 {root}")
            return 2
    else:
        root = find_kindle()
        if root is None:
            print("!! 未检测到 Kindle 分区（应含 system/version.txt）")
            print("   请确认：设备已用 USB 连接、已在 Kindle 上点『允许访问』、盘符可见")
            return 2

    r = scan_root(root)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0

    L = []
    L.append("=" * 70)
    L.append(f"  Kindle 设备报告    {r['root']}")
    L.append("=" * 70)
    L.append("")
    L.append(f"  固件版本      : {r['firmware']}")
    L.append(f"  架构推断      : {r['arch']}   -> KOReader 平台后缀 {r['platform_suffix']}")
    if r["free_gb"] is not None:
        L.append(f"  剩余 / 总空间 : {r['free_gb']} GB / {r['total_gb']} GB")

    if args.serial:
        model, plat = hint_model(args.serial)
        if model:
            L.append(f"  序列号        : {args.serial}  -> {model}（建议平台后缀 {plat}）")
        else:
            L.append(f"  序列号        : {args.serial}  -> 前缀未知，请用官方向导确认")
    else:
        L.append("  序列号        : 未提供（用 --serial 传入；或看 设置→设备选项→设备信息）")

    L.append("")
    L.append("-" * 70)
    L.append(f"  越狱状态      : {'已越狱' if r['jailbroken'] else '未越狱 / 未检测到'}")
    L.append("-" * 70)
    for p, desc in FIELDS:
        mark = "OK " if r["markers"].get(p) else "-- "
        L.append(f"   [{mark}] {p}")
        L.append(f"          {desc}")

    if r["pending_updates"]:
        L.append("")
        L.append("  !! 根目录存在待安装的系统更新文件（会顶掉可利用的固件版本）：")
        for n in r["pending_updates"]:
            L.append(f"       - {n}")
        L.append("     越狱前请删除这些文件。")
    else:
        L.append("")
        L.append("  根目录无待安装的 .bin 更新文件  OK")

    L.append("")
    L.append(f"  KPM 已装包    : {', '.join(r['kpm_packages']) if r['kpm_packages'] else '（无 / 未越狱）'}")
    L.append(f"  KOReader 插件 : {len(r['koreader_plugins'])} 个"
             + (f"  ({', '.join(r['koreader_plugins'][:8])}...)" if len(r['koreader_plugins']) > 8
                else (f"  ({', '.join(r['koreader_plugins'])})" if r['koreader_plugins'] else "")))

    L.append("")
    L.append(f"  词典          : 共 {len(r['dicts'])} 本 .ifo")
    if r["dicts_disabled"]:
        L.append(f"    已禁用      : {len(r['dicts_disabled'])} 本")
    if len(r["dicts"]) > 4 and not r["dicts_disabled"]:
        L.append("    !! 启用词典超过 4 本且未见禁用列表 -> 查词可能卡顿（见 fix_dict_lag.py）")
    for d in r["dicts"][:12]:
        L.append(f"      - {os.path.relpath(d['ifo'], r['root'])}")
    if len(r["dicts"]) > 12:
        L.append(f"      ... 其余 {len(r['dicts']) - 12} 本")

    d = r["documents"]
    L.append("")
    L.append(f"  documents     : {d['size_mb']} MB")
    if d["by_ext"]:
        L.append("    书籍        : " + ", ".join(
            f"{k}×{v}" for k, v in sorted(d["by_ext"].items(), key=lambda x: -x[1])))
    L.append(f"    .sdr 目录   : {d['sdr_total']} 个（其中空壳 {d['sdr_empty']} 个）")
    if d["junk_candidates"]:
        L.append(f"    垃圾候选    : {d['junk_candidates']} 个 -> 用 clean_device.py 预览")

    L.append("")
    L.append("=" * 70)
    if not r["jailbroken"]:
        L.append("  下一步：走越狱流程。先用官方向导确认方法：")
        L.append("          https://kindlemodding.org/jailbreak-wizard")
        L.append("          本地说明见 references/01-机型判定与越狱方式.md")
    elif not r["markers"].get("koreader/reader.lua"):
        L.append("  下一步：已越狱但未装 KOReader -> 阶段 4")
        L.append("          python fetch_kpm_catalog.py --download koreader --variant "
                 + r["platform_suffix"])
    else:
        L.append("  状态：越狱 + KOReader 均已就位。可进入可选增强阶段（references/03、04）")
    L.append("=" * 70)
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
