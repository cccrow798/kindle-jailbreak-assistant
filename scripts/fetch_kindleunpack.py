#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取 KindleUnpack（AZW3 -> EPUB 解封装工具）。

为什么不随技能内置：KindleUnpack 是 GPL 第三方代码，按需下载更干净，
也避免把第三方源码打包进发布的技能里。

性质说明：KindleUnpack **只做格式解封装，不涉及任何解密**。
          带 DRM 的书（encryption=2 / KFX）不在转换范围内。

用法：
    python fetch_kindleunpack.py                    # 下载到 ./tools/kindleunpack
    python fetch_kindleunpack.py --dir ./tools      # 指定目标目录
    python fetch_kindleunpack.py --check            # 只检查是否已存在
"""
import argparse
import os
import shutil
import sys
import urllib.request
import zipfile

SRC = "https://github.com/kevinhendricks/KindleUnpack/archive/refs/heads/master.zip"
PROXIES = ["", "https://ghfast.top/"]     # 直连失败时走加速前缀


def target_of(base):
    return os.path.join(base, "kindleunpack", "lib", "kindleunpack.py")


def find_existing(base):
    for p in (target_of(base),
              os.path.join(os.getcwd(), "tools", "kindleunpack", "lib", "kindleunpack.py")):
        if os.path.isfile(p):
            return p
    return None


def download(dest_zip):
    last = None
    for pref in PROXIES:
        url = (pref + SRC) if pref else SRC
        try:
            print(f"[下载] {url}")
            req = urllib.request.Request(url, headers={
                "User-Agent": "kindle-jailbreak-assistant/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r, open(dest_zip, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            # 校验确实是个 zip（防止拿到 HTML 错误页）
            if not zipfile.is_zipfile(dest_zip):
                raise IOError("下载内容不是合法 zip")
            return True
        except Exception as e:                              # noqa: BLE001
            last = e
            print(f"       失败：{e}")
            if os.path.isfile(dest_zip):
                os.remove(dest_zip)
    print(f"!! 全部下载源均失败：{last}")
    print("   可手动下载并解压到 tools/kindleunpack/：")
    print(f"   {SRC}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="./tools", help="目标目录（默认 ./tools）")
    ap.add_argument("--check", action="store_true", help="只检查是否已存在")
    args = ap.parse_args()

    base = os.path.abspath(args.dir)
    if args.check:
        p = find_existing(base)
        print(f"[已存在] {p}" if p else "[缺失] 未找到 kindleunpack.py，需先运行本脚本下载")
        return 0 if p else 1

    if find_existing(base):
        print(f"[跳过] 已存在 {find_existing(base)}")
        return 0

    os.makedirs(base, exist_ok=True)
    zpath = os.path.join(base, "_ku.zip")
    if not download(zpath):
        return 2

    tmp = os.path.join(base, "_ku_tmp")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp, exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(tmp)

    # 解压出来通常是 KindleUnpack-master/
    inner = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
    if not inner:
        print("!! 压缩包内没有目录，下载可能不完整")
        return 3
    final = os.path.join(base, "kindleunpack")
    if os.path.isdir(final):
        shutil.rmtree(final)
    os.rename(os.path.join(tmp, inner[0]), final)
    shutil.rmtree(tmp)
    os.remove(zpath)

    p = target_of(base)
    if not os.path.isfile(p):
        print(f"!! 解压后未找到 {p}，目录结构与预期不同")
        return 4
    lic = os.path.join(final, "COPYING.txt")
    print(f"[完成] {p}")
    if os.path.isfile(lic):
        print(f"       许可证随源码保留：{lic}（GPL）")
    print()
    print("下一步：")
    print(f"    KINDLEUNPACK={p} python convert_azw3.py F:/documents")
    print("    （若 convert_azw3.py 与本工具都在默认位置，会自动发现，不必设置环境变量）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
