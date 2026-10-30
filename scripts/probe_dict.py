# -*- coding: utf-8 -*-
"""
StarDict 词典探针：读 .ifo / .idx / .syn，统计词条数，并抽样验证某些词是否可查。
用于拷进 Kindle 前先确认「词条够不够、变形词查不查得到」。

用法:
    python probe_dict.py <词典目录 或 .ifo 文件> [要测试的词...]
示例:
    python probe_dict.py dict_new/ecdict gave teeth ubiquitous zzzqqq
"""
import os
import struct
import sys


def find_ifo(target):
    if os.path.isfile(target) and target.endswith(".ifo"):
        return target
    for root, _, files in os.walk(target):
        for f in files:
            if f.endswith(".ifo"):
                return os.path.join(root, f)
    return None


def read_ifo(path):
    info = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "=" in line:
                k, v = line.rstrip("\n").split("=", 1)
                info[k] = v
    return info


def read_idx(path, bits):
    """StarDict .idx: 词条(以 \0 结尾) + 4/8 字节 offset + 4 字节 size，大端"""
    if bits == 64:
        idx_fmt, idx_len = ">Q", 8
    else:
        idx_fmt, idx_len = ">L", 4
    entries = []          # (word, offset, size)
    with open(path, "rb") as f:
        data = f.read()
    pos = 0
    n = len(data)
    while pos < n:
        end = data.find(b"\x00", pos)
        if end < 0:
            break
        word = data[pos:end].decode("utf-8", errors="replace")
        pos = end + 1
        if pos + idx_len + 4 > n:
            break
        off = struct.unpack(idx_fmt, data[pos:pos + idx_len])[0]
        pos += idx_len
        size = struct.unpack(">L", data[pos:pos + 4])[0]
        pos += 4
        entries.append((word, off, size))
    return entries


def read_syn(path, bits):
    """StarDict .syn: 同义词(以 \0 结尾) + 4 字节「idx 中的序号」，大端"""
    syns = []
    if not os.path.isfile(path):
        return syns
    with open(path, "rb") as f:
        data = f.read()
    pos, n = 0, len(data)
    while pos < n:
        end = data.find(b"\x00", pos)
        if end < 0:
            break
        w = data[pos:end].decode("utf-8", errors="replace")
        pos = end + 1
        if pos + 4 > n:
            break
        num = struct.unpack(">L", data[pos:pos + 4])[0]
        pos += 4
        syns.append((w, num))
    return syns


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    target = sys.argv[1]
    words = sys.argv[2:]

    ifo = find_ifo(target)
    if not ifo:
        print(f"[错误] 在 {target} 里找不到 .ifo")
        return 1
    info = read_ifo(ifo)
    base = ifo[:-4]
    bits = int(info.get("idxoffsetbits", "32"))
    declared = int(info.get("wordcount", "0"))

    print(f"[词典] {info.get('bookname', '?')}")
    print(f"  文件       {os.path.basename(ifo)}")
    print(f"  声称词条   {declared:,}")
    print(f"  idx 偏移   {bits} bit")
    print(f"  同型序列   sametypesequence={info.get('sametypesequence', '(无，逐条带类型)')}")
    if info.get("lang"):
        print(f"  lang       {info['lang']}")

    idx_path = base + ".idx"
    if not os.path.isfile(idx_path):
        print("[错误] 缺 .idx")
        return 1
    entries = read_idx(idx_path, bits)
    print(f"  实测词条   {len(entries):,}"
          + ("  ⚠ 与声称不符" if declared and abs(len(entries) - declared) > max(10, declared * 0.01) else "  ✓ 一致"))
    print(f"  idx 体积   {os.path.getsize(idx_path)/1048576:.2f} MB")

    dict_path = base + ".dict.dz"
    if not os.path.isfile(dict_path):
        dict_path = base + ".dict"
    if os.path.isfile(dict_path):
        print(f"  正文体积   {os.path.getsize(dict_path)/1048576:.2f} MB  ({os.path.basename(dict_path)})")

    syn_path = base + ".syn"
    syns = read_syn(syn_path, bits)
    if syns:
        print(f"  变形/同义  {len(syns):,} 条 (.syn)")
    else:
        print("  变形/同义  无 .syn —— 变形词（gave/teeth…）可能查不到")

    if not words:
        print("\n[抽样] 未指定测试词，跳过。可在命令后加词，如: gave teeth ubiquitous")
        return 0

    lookup = {}
    for i, (w, *_rest) in enumerate(entries):
        lookup.setdefault(w, i)
    syn_lookup = {}
    for w, num in syns:
        syn_lookup.setdefault(w, num)

    print(f"\n[抽样测试] {len(words)} 个词")
    hit_direct = hit_form = miss = 0
    for w in words:
        wl = w.lower()
        if wl in lookup:
            print(f"   ✓ {w:16s} 直接收录（第 {lookup[wl]:,} 条）")
            hit_direct += 1
        elif wl in syn_lookup:
            n = syn_lookup[wl]
            head = entries[n][0] if 0 <= n < len(entries) else "?"
            print(f"   ~ {w:16s} 通过变形/同义表命中 → {head}")
            hit_form += 1
        else:
            print(f"   ✗ {w:16s} 查不到")
            miss += 1
    print(f"  小结：直接收录 {hit_direct} / 变形命中 {hit_form} / 查不到 {miss}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
