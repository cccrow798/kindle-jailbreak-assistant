"""解析 KOReader 内置词典清单 ui/data/dictionaries.lua，按语言对列出可下载词典。

用法: python list_dicts.py <dictionaries.lua 路径>
"""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"F:\koreader\frontend\ui\data\dictionaries.lua"
lines = open(path, encoding="utf-8", errors="replace").read().splitlines()

recs = []
cur = None
for ln in lines:
    m = re.match(r"\s*name\s*=\s*[\"'](.+?)[\"']", ln)
    if m:
        if cur:
            recs.append(cur)
        cur = {"name": m.group(1)}
        continue
    if cur is None:
        continue
    for key in ("lang_in", "lang_out", "license", "url"):
        mm = re.match(r"\s*" + key + r"\s*=\s*[\"'](.+?)[\"']", ln)
        if mm:
            cur[key] = mm.group(1)
    me = re.match(r"\s*entries\s*=\s*(\d+)", ln)
    if me:
        cur["entries"] = int(me.group(1))
    if re.match(r"\s*\},?\s*$", ln):
        recs.append(cur)
        cur = None
if cur:
    recs.append(cur)

print(f"清单总数: {len(recs)}\n")
pairs = [
    ("英英 eng→eng", "eng", "eng"),
    ("英汉 eng→zho", "eng", "zho"),
    ("汉英 zho→eng", "zho", "eng"),
    ("汉语 zho→zho", "zho", "zho"),
    ("英语→法语 eng→fra", "eng", "fra"),
]
for label, a, b in pairs:
    sel = [r for r in recs if r.get("lang_in") == a and r.get("lang_out") == b]
    sel.sort(key=lambda r: -(r.get("entries") or 0))
    print(f"--- {label}：{len(sel)} 本 ---")
    for r in sel[:18]:
        print(f"   {r['name'][:46]:48s} {r.get('entries', 0):>9,} 词条   {r.get('license', '')[:28]}")
    print()
