#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理 Kindle（越狱后 + KOReader）上的残留 / 冗余文件。

设计原则：
- **只删「清单内」且「落在白名单目录内」** 的路径，其它一律不碰
- 默认**只预览**，加 --go 才真正删除
- 不触碰：书籍（除显式 --azw3）、任何在用 .sdr 阅读记录、配置备份、正在启用的词典
- 白名单只允许 documents/ 与 koreader/data/dict/ 两处

用法：
    python clean_device.py F:                 # 预览，不删任何东西
    python clean_device.py F: --azw3          # 预览时把 azw3 也一并列出（仍不删）
    python clean_device.py F: --azw3 --go     # 执行（含 azw3，需已确认电脑备份）
    python clean_device.py F: --list          # 机器可读清单（制表符分隔）
"""
import argparse
import os
import re
import shutil
import sys
import time

BOOK_EXT_KEEP = (".epub", ".kfx", ".mobi", ".txt", ".pdf", ".azw")


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


def read_disabled_dicts(root):
    """从 koreader/settings.reader.lua 读出 dicts_disabled 的词典路径"""
    sp = os.path.join(root, "koreader", "settings.reader.lua")
    if not os.path.isfile(sp):
        return []
    try:
        with open(sp, "rb") as f:
            t = f.read().decode("utf-8", "surrogateescape")
    except OSError:
        return []
    m = re.search(r'\["dicts_disabled"\]\s*=\s*\{([^{}]*)\}', t)
    if not m:
        return []
    return re.findall(r'\["([^"]+)"\]\s*=\s*true', m.group(1))


def dict_dir_from_ifo(ifo):
    return os.path.dirname(ifo)


def collect(root, want_azw3):
    doc = os.path.join(root, "documents")
    dicts_root = os.path.join(root, "koreader", "data", "dict")
    junk_files, junk_dirs, books, dicts = [], [], [], []

    if not os.path.isdir(doc):
        print(f"!! 找不到 {doc}")
        return None

    try:
        entries = sorted(os.listdir(doc))
    except OSError as e:
        print(f"!! 无法列出 {doc}: {e}")
        return None

    for name in entries:
        p = os.path.join(doc, name)
        low = name.lower()

        # 空 .sdr 目录（内部无任何条目）
        if low.endswith(".sdr") and os.path.isdir(p):
            try:
                inner = os.listdir(p)
            except OSError:
                inner = ["?"]
            if not inner:
                junk_dirs.append(p)
            continue

        if not os.path.isfile(p):
            continue

        # 已知残留文件
        if low.endswith(".kfx.sd"):
            junk_files.append(p); continue
        if low.endswith(".tmp.sa.decompressed"):
            junk_files.append(p); continue
        if name.startswith(".fuse_hidden"):
            junk_files.append(p); continue
        if low.endswith(".tgz") and "crash" in low and "kppmainapp" in low.replace("_", ""):
            junk_files.append(p); continue

        # 可选：azw3（KOReader 不支持；删后原生阅读器也不再有，务必先核对备份）
        if want_azw3 and low.endswith(".azw3"):
            books.append(p); continue

    # 崩溃包遗留的 .sdr（非空，但归属崩溃组件）
    for name in entries:
        low = name.lower()
        if low.endswith(".sdr") and "kppmainapp" in low.replace("_", ""):
            p = os.path.join(doc, name)
            if os.path.isdir(p) and p not in junk_dirs:
                junk_dirs.append(p)

    # 已禁用的词典目录（从 settings.reader.lua 读，而不是硬编码）
    paths = read_disabled_dicts(root)
    seen = set()
    for d in paths:
        rel = d
        for pref in ("/mnt/us/koreader/", "mnt/us/koreader/"):
            if rel.startswith(pref):
                rel = rel[len(pref):]
        rel = rel.lstrip("/")
        cand = os.path.join(root, "koreader", rel)
        cand = os.path.dirname(cand) if cand.endswith(".ifo") else cand
        cand = os.path.normpath(cand)
        if cand in seen:
            continue
        seen.add(cand)
        if os.path.isdir(cand) and cand != os.path.normpath(dicts_root):
            dicts.append(cand)

    return junk_files, junk_dirs, books, dicts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("drive", nargs="?", default="F:")
    ap.add_argument("--go", action="store_true", help="真正执行删除（默认只预览）")
    ap.add_argument("--azw3", action="store_true", help="把 .azw3 也列为删除候选")
    ap.add_argument("--list", action="store_true", help="输出机器可读清单后退出")
    args = ap.parse_args()

    root = args.drive.rstrip("\\/") + os.sep
    if not os.path.isdir(root):
        print(f"!! 盘符不存在：{root}")
        return 2

    allow = [os.path.abspath(os.path.join(root, "documents")),
             os.path.abspath(os.path.join(root, "koreader", "data", "dict"))]

    def in_allow(p):
        ap_ = os.path.abspath(p)
        return any(ap_ == r or ap_.startswith(r + os.sep) for r in allow)

    got = collect(root, args.azw3)
    if got is None:
        return 3
    junk_files, junk_dirs, books, dicts = got

    groups = [("A 残留文件", junk_files),
              ("B 空/废弃目录", junk_dirs),
              ("C azw3（KOReader 不支持；删后原生阅读器也没了）", books),
              ("D 已禁用的词典", dicts)]

    if args.list:
        for label, items in groups:
            for p in items:
                print(f"{label}\t{os.path.relpath(p, root)}\t{sizeof(p)}")
        return 0

    # 白名单校验
    bad = [p for _, items in groups for p in items if not in_allow(p)]
    if bad:
        print("!! 以下路径不在白名单内，已中止：")
        for p in bad:
            print("   ", p)
        return 4

    # ---- 在用记录排除：含阅读状态的 .sdr 一律不允许出现在删除清单 ----
    doc = os.path.join(root, "documents")
    in_use = set()
    if os.path.isdir(doc):
        for n in os.listdir(doc):
            if not n.lower().endswith(".sdr"):
                continue
            d = os.path.join(doc, n)
            if not os.path.isdir(d):
                continue
            try:
                for f in os.listdir(d):
                    if f.endswith(".lua") or f.endswith(".mbp1") or f.endswith(".mbs") \
                       or f.endswith(".phl") or f.endswith(".asc"):
                        in_use.add(os.path.abspath(d))
                        break
            except OSError:
                pass
    overlap = [p for _, items in groups for p in items
               if os.path.abspath(p) in in_use]
    if overlap:
        print("!! 删除清单里出现了「有阅读记录」的 .sdr，已中止：")
        for p in overlap:
            print("   ", os.path.relpath(p, root))
        return 5

    total = 0
    print("=" * 74)
    for label, items in groups:
        if not items:
            continue
        s = sum(sizeof(p) for p in items)
        total += s
        print(f"  {label}: {len(items)} 项, {s/1048576:.1f} MB")
    print("-" * 74)
    print(f"  合计: {total/1048576:.1f} MB")
    print(f"  在用阅读记录（已排除，不会删）: {len(in_use)} 个 .sdr")
    print("=" * 74)

    for label, items in groups:
        if not items:
            continue
        print(f"\n【{label}】")
        for p in items:
            print(f"   {sizeof(p)/1024:10.1f} KB  {os.path.relpath(p, root)}")

    if not args.go:
        print()
        print("-" * 74)
        print("  [预览模式] 未删除任何文件。")
        print("  确认无误后加 --go 执行；删除必须在沙箱外运行（沙箱内遇 FAT32 必失败）。")
        print("-" * 74)
        return 0

    items_all = [p for _, items in groups for p in items]
    print(f"\n开始删除（共 {len(items_all)} 项）...")
    for p in items_all:
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
        except Exception as e:                              # noqa: BLE001
            print(f"   ! 失败 {os.path.relpath(p, root)}  {e}")

    # 复核：以「删前在清单内、删后不存在」为准（不依赖计数器）
    left = [p for p in items_all if os.path.exists(p)]
    print(f"\n完成：已清除 {len(items_all)-len(left)}/{len(items_all)} 项，残留 {len(left)} 项")
    for p in left[:20]:
        print(f"   · 未清除 {os.path.relpath(p, root)}")

    # 清单存档（存到设备之外，便于日后查证）
    stamp = time.strftime("%Y%m%d")
    out = os.path.abspath(os.path.join(root, os.pardir, f"_清理清单_{stamp}.txt"))
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"# Kindle 清理清单  {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 盘符 {root}\n\n")
            for label, items in groups:
                if not items:
                    continue
                f.write(f"## {label}\n")
                for p in items:
                    f.write(f"{'已删' if not os.path.exists(p) else '未删'}\t"
                            f"{os.path.relpath(p, root)}\t{sizeof(p)}\n")
            f.write(f"\n# 在用阅读记录（未删） {len(in_use)} 个\n")
            for p in sorted(in_use):
                f.write(f"在用\t{os.path.relpath(p, root)}\n")
        print(f"\n清单已存档：{out}")
    except OSError as e:
        print(f"\n（清单存档失败：{e}）")

    try:
        u = shutil.disk_usage(root)
        print(f"设备剩余空间：{u.free/2**30:.2f} GB")
    except OSError:
        pass
    print("\n提醒：改动后请重启 KOReader（词典与文件列表在启动时扫描）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
