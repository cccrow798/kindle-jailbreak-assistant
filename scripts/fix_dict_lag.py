#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断并修复「KOReader 查词卡顿」——根因是启用词典过多。

原理：查一个词时 KOReader 会依次跑一遍所有启用的词典；词典查询走 dismissablePopen，
      协程不可用时退化为阻塞 io.popen，直接卡住主线程。所以本数越多、卡得越明显。

本脚本会：
  1. 扫描 <盘>/koreader/data/dict 下所有 .ifo，读 bookname / wordcount
  2. 按语言归类（英英 / 英汉 / 汉英 / 汉汉 / 其它）
  3. 每类保留词条数最多的一本（上限 --max，默认 4）
  4. 其余写入 settings.reader.lua 的 dicts_disabled（**禁用而非删除**，随时可勾回）
  5. 同步精简每本书 .sdr/metadata.*.lua 里的 preferred_dictionaries
     （它**会覆盖**全局禁用，只改全局往往不生效）

用法：
    python fix_dict_lag.py --drive F:                 # 预览，不写任何东西
    python fix_dict_lag.py --drive F: --go            # 执行（先自动备份 settings.reader.lua）
    python fix_dict_lag.py --drive F: --max 3 --go    # 只保留 3 本
"""
import argparse
import os
import re
import shutil
import sys
import time

CATS = [
    # 顺序即匹配优先级：先判「汉英」，再判「英汉」，避免互相误判
    ("zh-en", ("汉英", "zh-en", "zh_en", "chinese-english", "c2e", "汉英词典")),
    ("en-zh", ("英汉", "en-zh", "en_zh", "english-chinese", "e2c", "ecdict",
               "简明英汉", "牛津", "朗文", "柯林斯", "21世纪", "新英汉", "英汉双解")),
    ("zh-zh", ("汉汉", "汉语", "中文", "新华", "现代汉语", "古汉语", "成语",
               "zh-zh", "zh_zh", "汉字")),
    ("en-en", ("英英", "en-en", "en_en", "english", "webster", "gcide", "wordnet",
               "reader.dict en", "wiktionary", "oxford", "collins", "century")),
]
# 兜底：other 归入这些类别（按顺序找第一个空缺的）
FALLBACK_ORDER = ["en-zh", "en-en", "zh-zh", "zh-en"]


def categorize(text):
    low = text.lower()
    for cat, keys in CATS:
        for k in keys:
            if k in low:
                return cat
    return "other"


def read_ifo(path):
    """读 StarDict .ifo 头部，取 bookname / wordcount"""
    info = {}
    try:
        with open(path, "rb") as f:
            head = f.read(8192)
        txt = head.decode("utf-8", "replace")
        for line in txt.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                info[k.strip().lower()] = v.strip()
    except OSError:
        pass
    return info


def scan_dicts(root):
    base = os.path.join(root, "koreader", "data", "dict")
    out = []
    if not os.path.isdir(base):
        return out
    for dirpath, _dirnames, filenames in os.walk(base):
        for fn in filenames:
            if not fn.lower().endswith(".ifo"):
                continue
            p = os.path.join(dirpath, fn)
            info = read_ifo(p)
            book = info.get("bookname", "")
            try:
                wc = int(info.get("wordcount", "0") or 0)
            except ValueError:
                wc = 0
            rel = os.path.relpath(p, base).replace(os.sep, "/")
            top = rel.split("/")[0]
            out.append({
                "ifo": p,
                "rel": rel,
                "top": top,
                "book": book,
                "wordcount": wc,
                "cat": categorize(f"{book} {rel}"),
            })
    return out


def to_device_path(root, local):
    """<盘>/koreader/... -> /mnt/us/koreader/..."""
    rel = os.path.relpath(local, root).replace(os.sep, "/")
    return "/mnt/us/" + rel


def read_text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "surrogateescape")


def write_text_fat(path, text):
    """FAT32 上不能覆盖改名：先删再写"""
    if os.path.exists(path):
        os.remove(path)
    with open(path, "wb") as f:
        f.write(text.encode("utf-8", "surrogateescape"))


def backup(path):
    b = path + ".bak-dictlag"
    if os.path.isfile(path) and not os.path.exists(b):
        shutil.copyfile(path, b)
        return b
    return b if os.path.exists(b) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive", default="F:")
    ap.add_argument("--max", type=int, default=4, help="最多启用几本（默认 4）")
    ap.add_argument("--keep", action="append", default=[], metavar="NAME",
                    help="强制保留的词典（可重复；取顶层目录名，如 en-en）")
    ap.add_argument("--go", action="store_true", help="真正写入（默认只预览）")
    args = ap.parse_args()
    pinned = list(args.keep or [])

    root = args.drive.rstrip("\\/") + os.sep
    if not os.path.isdir(root):
        print(f"!! 盘符不存在：{root}")
        return 2
    if not os.path.isdir(os.path.join(root, "koreader")):
        print("!! 该盘没有 koreader 目录，确认是不是 Kindle 分区")
        return 3

    dicts = scan_dicts(root)
    if not dicts:
        print("!! 未在 koreader/data/dict 找到任何 .ifo 词典")
        return 4

    sp = os.path.join(root, "koreader", "settings.reader.lua")
    disabled_now = set()
    if os.path.isfile(sp):
        t = read_text(sp)
        m = re.search(r'\["dicts_disabled"\]\s*=\s*\{([^{}]*)\}', t)
        if m:
            disabled_now = set(re.findall(r'\["([^"]+)"\]\s*=\s*true', m.group(1)))
    else:
        t = None

    enabled = [d for d in dicts if to_device_path(root, d["ifo"]) not in disabled_now]
    print("=" * 78)
    print(f"  KOReader 词典诊断   {root}")
    print("=" * 78)
    print(f"  词典总数      : {len(dicts)}")
    print(f"  当前启用      : {len(enabled)}  ->  "
          + (", ".join(d["top"] for d in enabled) if enabled else "（无）"))
    if len(enabled) <= args.max:
        print()
        print(f"  已达标（<= {args.max} 本），无需处理。")
        print("  若仍感觉查词慢，检查 crash.log 里是否出现：")
        print("    WARN unwrapped dismissablePopen(), falling back to blocking io.popen()")
        return 0

    # 每类挑词条数最多的
    keep, drop = [], []
    by_cat = {}
    for d in dicts:
        by_cat.setdefault(d["cat"], []).append(d)

    # 兜底：把 other 归入空缺的类别，避免占用一个"保留名额"却什么都没覆盖
    others = sorted(by_cat.pop("other", []), key=lambda x: -x["wordcount"])
    for d in others:
        target = next((c for c in FALLBACK_ORDER if c not in by_cat), None)
        d["cat"] = target or "other"
        by_cat.setdefault(d["cat"], []).append(d)

    for cat, items in sorted(by_cat.items(), key=lambda x: -max(i["wordcount"] for i in x[1])):
        items.sort(key=lambda x: -x["wordcount"])
        keep.append(items[0])
        drop.extend(items[1:])

    # --keep 指定的必须保留
    for name in pinned:
        hit = next((d for d in dicts if d["top"] == name or d["ifo"] == name), None)
        if hit and hit not in keep:
            keep.append(hit)
            print(f"  （按 --keep 强制保留 {name}）")
        elif hit is None:
            print(f"  !! --keep {name} 未在设备上找到，忽略")

    drop = [d for d in drop if d not in keep]
    # 去重（保留首次出现）
    seen, keep_u = set(), []
    for d in keep:
        if id(d) in seen:
            continue
        seen.add(id(d))
        keep_u.append(d)
    keep = keep_u

    # 超过上限时：优先保证「语言覆盖」——先砍同类的重复项，再砍词条数最小的
    if len(keep) > args.max:
        must = [d for d in keep if d["top"] in pinned or d["ifo"] in pinned]
        rest = [d for d in keep if d not in must]
        while len(must) + len(rest) > args.max and rest:
            cnt = {}
            for d in must + rest:
                cnt[d["cat"]] = cnt.get(d["cat"], 0) + 1
            # 候选 1：所在类别还有别的保留项 -> 砍掉它不损失语言覆盖
            cand = [d for d in rest if cnt[d["cat"]] > 1]
            pool = cand if cand else rest
            victim = min(pool, key=lambda x: x["wordcount"])
            rest.remove(victim)
            drop.append(victim)
        keep = must + rest

    print()
    print(f"  建议保留 {len(keep)} 本：")
    for d in keep:
        print(f"    + [{d['cat']:6s}] {d['top']:22s} {d['book'][:32]:34s} "
              f"{d['wordcount']:>9,} 词")
    print()
    print(f"  建议禁用 {len(drop)} 本（文件保留，随时可在 KOReader 里勾回）：")
    for d in drop:
        print(f"    - [{d['cat']:6s}] {d['top']:22s} {d['book'][:32]:34s} "
              f"{d['wordcount']:>9,} 词")

    if t is None:
        print("\n!! 找不到 settings.reader.lua，无法写入配置。先在 KOReader 里启动一次再试。")
        return 5

    # ---- 构造新的 dicts_disabled / dicts_order ----
    drop_paths = sorted({to_device_path(root, d["ifo"]) for d in drop})
    keep_paths = [to_device_path(root, d["ifo"]) for d in keep]

    disabled_block = "".join(f'        ["{k}"] = true,\n' for k in drop_paths)
    order_block = "".join(f'        ["{k}"] = {i},\n' for i, k in enumerate(keep_paths, 1))
    new = (f'    ["dict_presets"] = {{}},\n'
           f'    ["dicts_disabled"] = {{\n{disabled_block}    }},\n'
           f'    ["dicts_order"] = {{\n{order_block}    }},')
    if "\r\n" in t:
        new = new.replace("\n", "\r\n")

    pat = re.compile(r'    \["dict_presets"\] = \{\},\r?\n'
                     r'    \["dicts_disabled"\] = \{[^{}]*\},\r?\n'
                     r'    \["dicts_order"\] = \{[^{}]*\},')
    t2, n = pat.subn(new, t, count=1)
    if n == 0:
        print("\n!! settings.reader.lua 里没匹配到 dict_presets/dicts_disabled/dicts_order 段。")
        print("   可能这几个键还不存在。请在 KOReader 里打开过一次『词典设置』再重试。")
        return 6

    # ---- 书籍级 preferred_dictionaries ----
    keep_names = {d["book"] for d in keep if d["book"]}
    keep_names |= {d["top"] for d in keep}
    book_edits = []
    docs = os.path.join(root, "documents")
    if os.path.isdir(docs):
        for dirpath, _dn, filenames in os.walk(docs):
            if not dirpath.endswith(".sdr"):
                continue
            for fn in filenames:
                if not fn.endswith(".lua"):
                    continue
                mp = os.path.join(dirpath, fn)
                try:
                    mt = read_text(mp)
                except OSError:
                    continue
                m = re.search(r'\["preferred_dictionaries"\] = \{([^{}]*)\}', mt)
                if not m:
                    continue
                names = re.findall(r'\[\d+\] = "([^"]+)"', m.group(1))
                kept = [x for x in names if x in keep_names]
                if len(kept) == len(names):
                    continue
                if not kept:
                    print(f"   （跳过 {os.path.basename(dirpath)}：清单里没有保留项，避免清空）")
                    continue
                block = '["preferred_dictionaries"] = {\n'
                block += "".join(f'        [{i}] = "{x}",\n' for i, x in enumerate(kept, 1))
                block += "    }"
                book_edits.append((mp, mt[:m.start()] + block + mt[m.end():],
                                   names, kept))

    print()
    print(f"  书籍级 preferred_dictionaries 需改 {len(book_edits)} 处")
    for mp, _t, old, newl in book_edits[:10]:
        print(f"    {os.path.relpath(mp, root)}")
        print(f"        原: {old}")
        print(f"        改: {newl}")

    if not args.go:
        print()
        print("-" * 78)
        print("  [预览模式] 未写入任何文件。确认后加 --go 执行。")
        print("  说明：禁用 ≠ 删除，词典文件保留，之后可在 KOReader 词典设置里勾回。")
        print("-" * 78)
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    b = backup(sp)
    write_text_fat(sp, t2)
    print(f"\n[写入] settings.reader.lua  启用 {len(keep)} / 禁用 {len(drop)}"
          + (f"（备份 {os.path.basename(b)}）" if b else ""))

    done = 0
    for mp, nt, _o, _n in book_edits:
        try:
            backup(mp)
            write_text_fat(mp, nt)
            done += 1
        except Exception as e:                              # noqa: BLE001
            print(f"   ! 写入失败 {os.path.relpath(mp, root)}  {e}")
    print(f"[写入] 书籍级配置 {done}/{len(book_edits)} 处")

    print()
    print("=" * 78)
    print("  完成。下一步：安全弹出 -> 拔线 -> 重启 KOReader。")
    print("  回滚：把 settings.reader.lua.bak-dictlag 覆盖回去即可。")
    print(f"  记录时间 {stamp}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
