#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
独立复核 KPM 包在设备上的落盘结果：存在性 + 字节数 + SHA256 全量比对。

判定以「包内每个应落盘的文件」为基准，逐个去设备上找：
  0 不一致 + 0 缺失 才算通过。

用法：
    python verify_install.py --drive F: --package ./pkg/koreader_x.kpkg
    python verify_install.py --drive F: --package ./pkg/koreader_x.kpkg --list   # 只打印设备侧清单
"""
import argparse
import hashlib
import os
import posixpath
import sys
import tarfile
import time

CHUNK = 1 << 20


def sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(CHUNK)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()
    except OSError:
        return None


def safe_join(root, rel):
    rel = rel.replace("\\", "/").lstrip("/")
    parts = [p for p in posixpath.normpath(rel).split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        return None
    return os.path.join(root, *parts)


def read_pkg_id(tf, members):
    import json as _json
    for m in members:
        if m.name.endswith("manifest.json"):
            try:
                f = tf.extractfile(m)
                if f:
                    d = _json.loads(f.read().decode("utf-8", "replace"))
                    for k in ("id", "name", "package"):
                        if isinstance(d.get(k), str):
                            return d[k]
            except Exception:                               # noqa: BLE001
                pass
    tops = {m.name.split("/")[0] for m in members if "/" in m.name}
    tops = {t for t in tops if t not in ("extensions", "scriptlets")}
    return sorted(tops)[0] if tops else "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive", required=True)
    ap.add_argument("--package", required=True)
    ap.add_argument("--list", action="store_true", help="只打印设备侧文件清单，不做比对")
    ap.add_argument("--save", default=None, help="把清单存成文件")
    args = ap.parse_args()

    drive = args.drive.rstrip("\\/") + os.sep
    if not os.path.isdir(drive):
        print(f"!! 盘符不存在：{drive}")
        return 2
    if not os.path.isfile(args.package):
        print(f"!! 找不到包：{args.package}")
        return 2

    has_extensions = os.path.isdir(os.path.join(drive, "extensions"))

    with tarfile.open(args.package, "r:*") as tf:
        members = [m for m in tf.getmembers() if m.isfile()]
        pkg_id = read_pkg_id(tf, members)

        expected = []       # (member_name, dst, size, sha256)
        skipped = 0
        for m in members:
            name = m.name
            if name == "extensions" or name.startswith("extensions/"):
                if not has_extensions:
                    skipped += 1
                    continue
                dst = safe_join(os.path.join(drive, "extensions"), name[len("extensions/"):])
            elif name == pkg_id or name.startswith(pkg_id + "/"):
                dst = safe_join(os.path.join(drive, pkg_id), name[len(pkg_id):].lstrip("/"))
            elif name.startswith("scriptlets/"):
                dst = safe_join(os.path.join(drive, "documents"), posixpath.basename(name))
            else:
                dst = safe_join(os.path.join(drive, "kmc", "kpm", "packages", pkg_id), name)
            if dst is None:
                continue
            f = tf.extractfile(m)
            data = f.read() if f else b""
            expected.append((name, dst, len(data), hashlib.sha256(data).hexdigest()))

        print("=" * 78)
        print(f"  复核 {os.path.basename(args.package)}   (包 id: {pkg_id})")
        print(f"  应落盘文件 {len(expected)} 个"
              + (f"，因无 extensions 目录跳过 {skipped} 个" if skipped else ""))
        print("=" * 78)

        if args.list:
            lines = ["\t".join([os.path.relpath(d, drive), str(s), h])
                     for _, d, s, h in expected]
            for ln in lines:
                print(ln)
            if args.save:
                with open(args.save, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                print(f"\n清单已存 {args.save}")
            print(f"\n（--list 模式：只列清单，未做校验）共 {len(expected)} 行")
            return 0

        t0 = time.time()
        missing, mismatch, ok = [], [], 0
        for i, (name, dst, size, want) in enumerate(expected, 1):
            if not os.path.isfile(dst):
                missing.append(name)
            else:
                actual_size = os.path.getsize(dst)
                if actual_size != size:
                    mismatch.append((name, f"大小 {actual_size} != {size}"))
                else:
                    got = sha256_file(dst)
                    if got != want:
                        mismatch.append((name, f"sha256 {str(got)[:12]} != {want[:12]}"))
                    else:
                        ok += 1
            if i % 200 == 0 or i == len(expected):
                print(f"\r    校验中 {i}/{len(expected)} ...", end="", flush=True)
        print()

        # 关键路径
        key = [("程序本体", os.path.join(drive, pkg_id)),
               ("图书馆入口", os.path.join(drive, "documents")),
               ("包管理元数据", os.path.join(drive, "kmc", "kpm", "packages", pkg_id))]
        print()
        print("  关键路径：")
        for label, p in key:
            print(f"    {'OK ' if os.path.exists(p) else '!! '} {label:<12s} {os.path.relpath(p, drive)}")

        launch = os.path.join(drive, "kmc", "kpm", "packages", pkg_id, "launch.sh")
        print(f"    {'OK ' if os.path.isfile(launch) else '!! '} launch.sh    "
              + os.path.relpath(launch, drive))

        scripts = [f for f in os.listdir(os.path.join(drive, "documents"))
                   if f.lower().endswith(".sh")] \
            if os.path.isdir(os.path.join(drive, "documents")) else []
        sh_hits = [s for s in scripts if pkg_id.lower().replace("-", "") in s.lower().replace("-", "")] \
            or scripts
        print(f"    {'OK ' if sh_hits else '!! '} scriptlet    "
              + (", ".join(sh_hits[:4]) if sh_hits else "documents 下没有 .sh"))

        print()
        print("=" * 78)
        print(f"  结果：一致 {ok} / 缺失 {len(missing)} / 不一致 {len(mismatch)}"
              f"   用时 {time.time()-t0:.1f}s")
        if missing:
            print("  缺失（前 20）：")
            for n in missing[:20]:
                print(f"    - {n}")
        if mismatch:
            print("  不一致（前 20）：")
            for n, why in mismatch[:20]:
                print(f"    - {n}: {why}")
        if not missing and not mismatch:
            print("  ✅ 全部通过（0 缺失 / 0 不一致）。")
            print("  下一步：安全弹出 -> 拔线 -> 重启一次 Kindle，然后在图书馆点图标启动。")
        else:
            print("  ❌ 未通过。常见原因：写入被中断（改用后台执行）、空间不足、数据线/USB 口不稳。")
            print("     处理：重跑 install_kpm_package.py --go --force 补齐，再复核一次。")
        print("=" * 78)
        return 0 if (not missing and not mismatch) else 1


if __name__ == "__main__":
    sys.exit(main())
