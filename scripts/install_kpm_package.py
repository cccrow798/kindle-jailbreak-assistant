#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把官方 KPM 包（.kpkg = tar.gz）离线安装到已越狱的 Kindle。

效果与在设备上执行 `;kpm install <id>` 完全一致，但不需要设备联网。

落盘规则（对齐官方 install.sh）：
    koreader/            -> <盘>:/koreader/                 程序本体
    scriptlets/<X>.sh    -> <盘>:/documents/<X>.sh          图书馆入口
    extensions/...       -> 仅当设备已存在 extensions 目录才拷（KUAL 用，一般跳过）
    其它（manifest.json / install.sh / launch.sh / DO_NOT_EDIT ...）
                         -> <盘>:/kmc/kpm/packages/<id>/    包管理元数据

设计约束：
- 默认**只预览**，必须显式加 --go 才写入
- FAT32 上「覆盖 / 改名」会失败：目标已存在时先 os.remove 再新建
- 拒绝绝对路径、.. 逃逸、符号链接（FAT 不支持 symlink）
- 每写一个文件即比对 SHA256，结束给汇总

用法：
    python install_kpm_package.py --drive F: --package ./pkg/koreader_x.kpkg          # 预览
    python install_kpm_package.py --drive F: --package ./pkg/koreader_x.kpkg --go     # 执行
"""
import argparse
import hashlib
import io
import json
import os
import posixpath
import sys
import tarfile

CHUNK = 1 << 20


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def safe_join(root, rel):
    """把 tar 内的相对路径安全地拼到 root 下；不合法返回 None"""
    rel = rel.replace("\\", "/").lstrip("/")
    if not rel or rel.startswith("../") or "/../" in rel or rel == "..":
        return None
    norm = posixpath.normpath(rel)
    if norm.startswith("../") or norm == "..":
        return None
    parts = [p for p in norm.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    return os.path.join(root, *parts)


def read_pkg_meta(tf, members):
    """从包内 manifest.json 取 id；取不到就用顶层目录名"""
    for m in members:
        if m.name.endswith("manifest.json"):
            try:
                f = tf.extractfile(m)
                if f:
                    d = json.loads(f.read().decode("utf-8", "replace"))
                    for k in ("id", "name", "package"):
                        if isinstance(d.get(k), str):
                            return d[k], d
            except Exception:                               # noqa: BLE001
                pass
    tops = {m.name.split("/")[0] for m in members if "/" in m.name}
    tops = {t for t in tops if t not in ("extensions", "scriptlets")}
    return (sorted(tops)[0] if tops else "unknown"), {}


def plan(tf, members, pkg_id, drive, has_extensions):
    """返回 [(member, dst, action)]，action in {write, skip_ext, skip_link, bad}"""
    rows = []
    for m in members:
        name = m.name
        if name.endswith("/"):
            continue
        if not (m.isfile() or m.issym() or m.islnk()):
            continue
        if name == "extensions" or name.startswith("extensions/"):
            rows.append((m, None, "skip_ext"))
            continue
        if m.issym() or m.islnk():
            rows.append((m, None, "skip_link"))
            continue
        if name == pkg_id or name.startswith(pkg_id + "/"):
            rel = name[len(pkg_id):].lstrip("/")
            dst = safe_join(os.path.join(drive, pkg_id), rel)
        elif name.startswith("scriptlets/"):
            base = posixpath.basename(name)
            if not base or base.startswith("."):
                rows.append((m, None, "bad"))
                continue
            dst = safe_join(os.path.join(drive, "documents"), base)
        else:
            dst = safe_join(os.path.join(drive, "kmc", "kpm", "packages", pkg_id), name)
        if dst is None:
            rows.append((m, None, "bad"))
            continue
        rows.append((m, dst, "write"))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive", required=True, help="Kindle 盘符，如 F:")
    ap.add_argument("--package", required=True, help=".kpkg / .tar.gz 路径")
    ap.add_argument("--go", action="store_true", help="真正写入（默认只预览）")
    ap.add_argument("--force", action="store_true", help="允许覆盖已存在且内容不同的文件")
    args = ap.parse_args()

    drive = args.drive.rstrip("\\/") + os.sep
    if not os.path.isdir(drive):
        print(f"!! 盘符不存在：{drive}")
        return 2
    if not os.path.isfile(os.path.join(drive, "system", "version.txt")):
        print(f"!! {drive} 看起来不是 Kindle 分区（缺 system/version.txt）")
        return 2
    if not os.path.isfile(args.package):
        print(f"!! 找不到包：{args.package}")
        return 2

    has_extensions = os.path.isdir(os.path.join(drive, "extensions"))
    has_kpm = os.path.isdir(os.path.join(drive, "kmc", "kpm"))

    try:
        tf = tarfile.open(args.package, "r:*")
    except Exception as e:                                  # noqa: BLE001
        print(f"!! 打开失败（可能不是 tar.gz）：{e}")
        return 3

    with tf:
        members = tf.getmembers()
        pkg_id, meta = read_pkg_meta(tf, members)
        rows = plan(tf, members, pkg_id, drive, has_extensions)

        writes = [r for r in rows if r[2] == "write"]
        sk_ext = [r for r in rows if r[2] == "skip_ext"]
        sk_link = [r for r in rows if r[2] == "skip_link"]
        bad = [r for r in rows if r[2] == "bad"]
        total = sum(m.size for m, _, a in writes if a == "write")

        print("=" * 78)
        print(f"  KPM 离线安装   {os.path.basename(args.package)}")
        print("=" * 78)
        print(f"  包 id         : {pkg_id}")
        if meta.get("name"):
            print(f"  包名          : {meta.get('name')}")
        if meta.get("version"):
            print(f"  版本          : {meta.get('version')}")
        print(f"  目标盘        : {drive}")
        print(f"  设备已有 kmc  : {'是' if has_kpm else '否（会自动创建）'}")
        print(f"  设备有 extensions: {'是（会一并安装 KUAL 部分）' if has_extensions else '否（跳过 extensions/）'}")
        print()
        print(f"  待写入文件    : {len(writes)} 个，合计 {total/1048576:.1f} MB")
        print(f"  跳过 extensions: {len(sk_ext)} 个")
        print(f"  跳过符号链接  : {len(sk_link)} 个")
        if bad:
            print(f"  !! 非法路径    : {len(bad)} 个（已拒绝）")
            for m, _, _ in bad[:10]:
                print(f"       - {m.name}")

        # 落点分布
        buckets = {}
        for m, dst, a in writes:
            if dst is None:
                continue
            key = os.path.relpath(os.path.dirname(dst), drive).split(os.sep)[0]
            b = buckets.setdefault(key, [0, 0])
            b[0] += 1
            b[1] += m.size
        print()
        print("  落点分布：")
        for k in sorted(buckets):
            n, s = buckets[k]
            print(f"     {k + os.sep:<28s} {n:5d} 个   {s/1048576:8.2f} MB")

        # 关键文件确认
        print()
        print("  关键路径确认：")
        for want in (f"{pkg_id}/", "documents/"):
            hit = [d for _, d, a in writes
                   if d and os.path.relpath(d, drive).replace(os.sep, "/").startswith(want)]
            print(f"     {want:<20s} {'OK ' if hit else '!! '} "
                  + (f"{len(hit)} 个文件" if hit else "未在包内找到"))

        if not writes:
            print("\n  !! 包内没有可写入的文件，检查包是否完整。")
            return 4

        if not args.go:
            print()
            print("-" * 78)
            print("  [预览模式] 未写入任何文件。确认无误后加 --go 执行。")
            print("  提示：写入量较大时请用后台执行，避免命令超时被打断。")
            print("-" * 78)
            return 0

        # ---------- 执行 ----------
        print()
        print("-" * 78)
        print("  开始写入 ...")
        ok = skipped = failed = 0
        fails = []
        done_bytes = 0
        for i, (m, dst, a) in enumerate(writes, 1):
            try:
                f = tf.extractfile(m)
                if f is None:
                    raise IOError("无法读取该成员")
                data = f.read()
                want = sha256_bytes(data)

                if os.path.isfile(dst):
                    with open(dst, "rb") as g:
                        cur = g.read()
                    if sha256_bytes(cur) == want:
                        skipped += 1
                        continue
                    if not args.force:
                        # 内容不同：覆盖会破坏既有安装，默认拒绝
                        failed += 1
                        fails.append((m.name, "目标已存在且内容不同（加 --force 才覆盖）"))
                        continue
                    os.remove(dst)          # FAT32：先删再建，不能用 os.replace

                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as o:
                    o.write(data)
                with open(dst, "rb") as g:
                    if sha256_bytes(g.read()) != want:
                        raise IOError("写入后校验不符")
                ok += 1
                done_bytes += len(data)
            except Exception as e:                          # noqa: BLE001
                failed += 1
                fails.append((m.name, str(e)))
            if i % 100 == 0 or i == len(writes):
                print(f"\r    {i}/{len(writes)}  写入 {ok} 跳过 {skipped} 失败 {failed} "
                      + f"{done_bytes/1048576:7.1f} MB", end="", flush=True)
        print()

        print()
        print("=" * 78)
        print(f"  完成：写入 {ok} / 内容一致跳过 {skipped} / 失败 {failed}")
        if fails:
            print("  失败清单（前 20）：")
            for n, why in fails[:20]:
                print(f"    - {n}: {why}")
        print()
        print("  下一步：")
        print("    1) python verify_install.py --drive "
              + args.drive + " --package \"" + args.package + "\"")
        print("    2) 安全弹出 -> 拔线 -> 重启一次 Kindle（让 scriptlet 重新索引）")
        print(f"    3) 图书馆点图标启动；或搜索框输入  ;kpm launch {pkg_id}")
        print("=" * 78)
        return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
