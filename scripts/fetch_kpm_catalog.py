#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
列出 / 下载官方 KPM 包（KindleModding/repo）。

关键点：仓库里 packages/*/artifacts/*.kpkg 走 Git LFS，
        raw / jsDelivr 拿到的是 1xx 字节的「指针文本」而非包本体。
        必须用 media.githubusercontent.com 的 media 地址下载；
        SHA256 与真实体积就在指针文本里，可直接用于校验。

用法：
    python fetch_kpm_catalog.py                                  # 列出全部包
    python fetch_kpm_catalog.py --filter koreader                # 只看匹配的
    python fetch_kpm_catalog.py --download koreader --variant kindlepw2 -o ./pkg
    python fetch_kpm_catalog.py --proxy https://ghfast.top/      # 走加速前缀（raw 抓取用）

只下载到本地目录，不写设备。
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

REPO = "KindleModding/repo"
BRANCH = "main"
UA = {"User-Agent": "kindle-jailbreak-assistant/1.0"}


def _open(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout)


def get_json(url, timeout=60):
    with _open(url, timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def get_text(url, timeout=60, proxy=None, retries=3):
    last = None
    for attempt in range(retries):
        try:
            if proxy:
                url = proxy.rstrip("/") + "/" + url
            with _open(url, timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:                              # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def tree():
    url = f"https://api.github.com/repos/{REPO}/git/trees/HEAD?recursive=1"
    try:
        data = get_json(url, timeout=90)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("!! GitHub API 触发了限流（未登录每小时 60 次）。稍后重试，")
            print("   或直接用官方发布页手动下载：")
            print(f"   https://github.com/{REPO}/tree/{BRANCH}/packages")
            return None
        raise
    if "tree" not in data:
        print(f"!! 返回异常：{str(data)[:300]}")
        return None
    return data["tree"]


def parse_pointer(text):
    """解析 Git LFS 指针文本，取 oid(sha256) 与 size"""
    oid, size = None, None
    if "oid sha256:" in text:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("oid sha256:"):
                oid = line.split("sha256:", 1)[1].strip()
            elif line.startswith("size "):
                try:
                    size = int(line.split()[1])
                except (IndexError, ValueError):
                    pass
    return oid, size


def collect(tree_items, proxy=None, quiet=False):
    """返回 [(pkg_id, filename, path, sha256, size)]"""
    arts = [t for t in tree_items
            if t["path"].endswith(".kpkg") and "/artifacts/" in t["path"]]
    out = []
    for t in arts:
        path = t["path"]
        parts = path.split("/")
        pkg_id = parts[1] if len(parts) > 1 else "?"
        fn = os.path.basename(path)
        raw = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"
        sha = size = None
        try:
            txt = get_text(raw, timeout=30, proxy=proxy)
            sha, size = parse_pointer(txt)
        except Exception as e:                              # noqa: BLE001
            if not quiet:
                print(f"  (指针读取失败 {fn}: {e})")
        out.append((pkg_id, fn, path, sha, size))
    return out


def fmt_size(n):
    if not n:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def guess_variant(fn, firmware=None):
    """从文件名判断平台后缀"""
    low = fn.lower()
    if "kindlepw2" in low:
        return "kindlepw2"
    if "kindlehf" in low:
        return "kindlehf"
    if "kindle" in low:
        return "kindle?"
    return "?"


def download(pkg_id, variant, outdir, proxy=None):
    items = tree()
    if items is None:
        return 2
    cands = collect(items, proxy=proxy, quiet=True)
    sel = [c for c in cands if c[0] == pkg_id]
    if variant:
        sel2 = [c for c in sel if variant.lower() in c[1].lower()]
        if sel2:
            sel = sel2
    if not sel:
        print(f"!! 未找到包 '{pkg_id}'"
              + (f"（平台 {variant}）" if variant else ""))
        print("   可用包：")
        for pid in sorted({c[0] for c in cands}):
            print(f"     - {pid}")
        return 2

    # 同一版本存在多个平台变体时，必须显式指定，避免装错架构
    if len(sel) > 1:
        latest = max(sel, key=lambda x: x[1])[1]
        same_ver = [c for c in sel if c[1].rsplit("_", 1)[0] == latest.rsplit("_", 1)[0]]
        variants = sorted({guess_variant(c[1]) for c in same_ver})
        if len(variants) > 1:
            print(f"!! 包 '{pkg_id}' 的同一版本存在多个平台变体：{', '.join(variants)}")
            print("   必须显式指定 --variant，装错架构会导致程序无法启动。")
            print(f"   老机型（PW1-3/KT2-3/K4-5 等）用 kindlepw2；较新机型（PW4+/KO/Scribe）用 kindlehf。")
            for c in sorted(same_ver, key=lambda x: x[1]):
                print(f"     {c[1]}")
            return 2

    c = sorted(sel, key=lambda x: x[1])[-1]     # 同名按文件名最大的一个
    pkg_id, fn, path, sha, size = c
    os.makedirs(outdir, exist_ok=True)
    dst = os.path.join(outdir, fn)
    url = f"https://media.githubusercontent.com/media/{REPO}/{BRANCH}/{path}"
    print(f"[下载] {pkg_id} / {fn}")
    print(f"       预期体积 {fmt_size(size)}   SHA256 {sha or '(未知)'}")
    print(f"       地址 {url}")

    tmp = dst + ".part"
    h = hashlib.sha256()
    got = 0
    try:
        with _open(url, timeout=600) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or (size or 0))
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
                h.update(b)
                got += len(b)
                if total:
                    pct = got * 100 / total
                    print(f"\r       进度 {pct:5.1f}%  {fmt_size(got)}/{fmt_size(total)}",
                          end="", flush=True)
        print()
    except Exception as e:                                  # noqa: BLE001
        print(f"\n!! 下载失败：{e}")
        if os.path.isfile(tmp):
            os.remove(tmp)
        return 3

    digest = h.hexdigest()
    # media 地址拿到的是真包（体积应远大于 1KB）；若仍是指针文本说明地址被改写
    if os.path.getsize(tmp) < 4096:
        with open(tmp, "r", errors="ignore") as f:
            head = f.read(200)
        if "oid sha256" in head:
            os.remove(tmp)
            print("!! 拿到的是 Git LFS 指针文本而不是包本体。")
            print("   请检查网络是否把 media.githubusercontent.com 重定向了。")
            return 4

    if sha and digest != sha:
        os.remove(tmp)
        print(f"!! SHA256 不匹配\n   期望 {sha}\n   实际 {digest}")
        print("   已删除损坏文件，请重试或换网络。")
        return 5

    if os.path.isfile(dst):
        os.remove(dst)
    os.rename(tmp, dst)
    print(f"[完成] {dst}  {fmt_size(os.path.getsize(dst))}  SHA256 OK")
    print(f"[下一步] python install_kpm_package.py --drive F: --package \"{dst}\"")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", default=None, help="只显示路径/文件名含该关键字的包")
    ap.add_argument("--download", default=None, metavar="PKG_ID", help="下载指定包 id")
    ap.add_argument("--variant", default=None, help="平台后缀，如 kindlepw2 / kindlehf")
    ap.add_argument("-o", "--out", default="./pkg", help="下载输出目录")
    ap.add_argument("--proxy", default=None, help="raw 抓取用的加速前缀，如 https://ghfast.top/")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.download:
        return download(args.download, args.variant, args.out, proxy=args.proxy)

    items = tree()
    if items is None:
        return 2
    rows = collect(items, proxy=args.proxy)
    if args.filter:
        rows = [r for r in rows if args.filter.lower() in r[2].lower()]

    if args.json:
        print(json.dumps([{"id": a, "file": b, "path": c, "sha256": d, "size": e}
                          for a, b, c, d, e in rows], ensure_ascii=False, indent=1))
        return 0

    if not rows:
        print("未找到 .kpkg 包。")
        return 0

    by_id = {}
    for a, b, c, d, e in rows:
        by_id.setdefault(a, []).append((b, d, e))

    print("=" * 96)
    print("  官方 KPM 包清单   https://github.com/%s" % REPO)
    print("=" * 96)
    for pid in sorted(by_id):
        print(f"\n  [{pid}]")
        for fn, sha, size in sorted(by_id[pid]):
            v = guess_variant(fn)
            print(f"     {fn:58s} {v:10s} {fmt_size(size):>9s}")
            if sha:
                print(f"        sha256 {sha}")
    print()
    print("-" * 96)
    print("  平台后缀：老机型（PW1-3/KT2-3/K4-5 等）用 kindlepw2；较新机型（PW4+/KO/Scribe）用 kindlehf")
    print("  两者不可混用。架构分界：固件 5.16.3 起为 hard-float，5.16.2.1.1 及以前为 soft-float。")
    print()
    print("  下载示例：")
    print("     python fetch_kpm_catalog.py --download koreader --variant kindlepw2 -o ./pkg")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
