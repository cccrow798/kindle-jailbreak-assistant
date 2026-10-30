# -*- coding: utf-8 -*-
"""
AZW3(KF8) -> EPUB 批量转换
- 只处理 scan_ebooks.py 判定为「无加密」的 KF8 文件（不涉及任何解密）
- 用 KindleUnpack 解包，产出标准 EPUB2
- 每本书用**独立且每次运行全新**的输出目录：
  KindleUnpack 会把输出目录下的所有文件打进 EPUB，复用目录会把上一本的残留
  累积进去（实测能把 0.8MB 的书撑到 259MB），务必隔离
- 三重校验：① 结构（mimetype/container.xml/OPF/章节/zip 完整性）
            ② 体积合理性（相对源文件不应膨胀）
            ③ 污染检测（zip 内媒体文件数不应远超 OPF 声明条目）
- 台账 _converted_ok.json 记录本次流程产出的合格文件，只有台账内的文件才会被跳过，
  避免把历史遗留的不合格产物当成合格件
- 全程只在系统临时目录写入，不删除任何文件

用法: python convert_azw3.py [源目录] [输出目录]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else "F:/documents"
WORKROOT = os.environ.get("KINDLE_JB_WORK") or os.path.join(os.getcwd(), "kindle_work")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(WORKROOT, "epub_out")

# ---- 定位 KindleUnpack ----
KU_CANDS = [
    os.environ.get("KINDLEUNPACK"),
    os.path.join(HERE, "tools", "kindleunpack", "lib", "kindleunpack.py"),
    os.path.join(os.getcwd(), "tools", "kindleunpack", "lib", "kindleunpack.py"),
    os.path.join(WORKROOT, "tools", "kindleunpack", "lib", "kindleunpack.py"),
]
KU = next((p for p in KU_CANDS if p and os.path.isfile(p)), None)
if KU is None:
    print("=" * 74)
    print("  缺少 KindleUnpack（只做格式解封装，不涉及任何解密；GPL 许可）")
    print("=" * 74)
    print("  下载并解压到本脚本同级的 tools/ 下：")
    print()
    print("    mkdir -p tools && cd tools")
    print("    curl -L -o ku.zip \\")
    print("      'https://ghfast.top/https://github.com/kevinhendricks/KindleUnpack/archive/refs/heads/master.zip'")
    print("    unzip ku.zip && mv KindleUnpack-master kindleunpack && rm ku.zip")
    print()
    print("  或用环境变量指定已有副本：")
    print("    KINDLEUNPACK=/path/to/kindleunpack.py python convert_azw3.py F:/documents")
    print("=" * 74)
    sys.exit(9)

RUNID = time.strftime("%Y%m%d-%H%M%S")
WORK = os.path.join(tempfile.gettempdir(), "kindle_epub_conv", RUNID)
SCAN = os.path.join(WORKROOT, "_ebook_scan.json")
LEDGER = os.path.join(WORKROOT, "_converted_ok.json")
PY = sys.executable
MEDIA_EXT = (".xhtml", ".html", ".htm", ".jpg", ".jpeg", ".png", ".gif", ".svg",
             ".ttf", ".otf", ".woff", ".css")

os.makedirs(OUT, exist_ok=True)
os.makedirs(WORK, exist_ok=True)


def validate(epub, src_size=None):
    """结构 + 体积 + 污染 三重校验"""
    if not zipfile.is_zipfile(epub):
        return False, "不是 zip"
    try:
        z = zipfile.ZipFile(epub)
    except Exception as e:
        return False, f"打开失败 {e}"
    names = z.namelist()
    if "mimetype" not in names:
        return False, "缺 mimetype"
    if z.read("mimetype") != b"application/epub+zip":
        return False, "mimetype 内容错误"
    if "META-INF/container.xml" not in names:
        return False, "缺 container.xml"
    opf = [n for n in names if n.lower().endswith(".opf")]
    if not opf:
        return False, "缺 OPF"
    meta = z.read(opf[0]).decode("utf-8", "replace")
    html = [n for n in names if n.lower().endswith((".xhtml", ".html", ".htm"))]
    if not html:
        return False, "没有任何正文文件"
    # 注意：小书整本可能只生成 1 个 xhtml，这属正常；改为看正文总字节数
    textbytes = sum(z.getinfo(n).file_size for n in html)
    if textbytes < 8192:
        return False, f"正文内容过少({textbytes/1024:.0f}KB)"
    if z.testzip() is not None:
        return False, "zip 内部损坏"
    z.close()
    # ② 体积
    if src_size:
        sz = os.path.getsize(epub)
        if sz > src_size * 2.2 + 6 * 1048576:
            return False, f"体积异常 {sz/1048576:.1f}MB（源 {src_size/1048576:.1f}MB）"
    # ③ 污染
    declared = meta.count("<item")
    media = [n for n in names if n.lower().endswith(MEDIA_EXT)]
    if len(media) > declared * 1.6 + 12:
        return False, f"疑似混入其他书内容（OPF 声明 {declared} 项 / 实际媒体 {len(media)} 个）"
    return True, f"{len(html)} 节/{len(media)} 资源"


def safe_dir(stem, i):
    s = re.sub(r'[\\/:*?"<>|]', "_", stem)[:60]
    return os.path.join(WORK, f"{i:03d}_{s}")


def main():
    if not os.path.isfile(SCAN):
        print("=" * 74)
        print(f"  缺少体检台账：{SCAN}")
        print("=" * 74)
        print("  必须先跑一次体检（只读文件头，判断哪些书无 DRM 可转）：")
        print()
        print(f"    python scan_ebooks.py {SRC}")
        print()
        print("  然后用同一个工作目录再跑本脚本：")
        print(f"    KINDLE_JB_WORK={WORKROOT} python convert_azw3.py {SRC}")
        print("=" * 74)
        return 8
    with open(SCAN, encoding="utf-8") as f:
        data = json.load(f)
    try:
        with open(LEDGER, encoding="utf-8") as f:
            ledger = json.load(f)
    except Exception:
        ledger = {}
    books = [r for r in data["clean"] if "KF8" in r.get("type", "")]
    print(f"待转换 KF8 书籍 {len(books)} 本 → {OUT}")
    print(f"本次运行工作区: {WORK}")
    print(f"台账已有 {len(ledger)} 条（仅台账内且仍合格的文件才跳过）")
    ok = skip = fail = 0
    fails = []
    t0 = time.time()
    for i, r in enumerate(books, 1):
        name = r["file"]
        stem = os.path.splitext(name)[0]
        src = os.path.join(SRC, name)
        dst = os.path.join(OUT, stem + ".epub")
        tag = f"[{i}/{len(books)}] {stem[:40]}"
        src_size = os.path.getsize(src) if os.path.isfile(src) else None
        rec = ledger.get(stem)
        if (rec and os.path.isfile(dst) and os.path.getsize(dst) == rec.get("size")
                and os.path.getsize(dst) > 20 * 1024):
            good, info = validate(dst, src_size)
            if good:
                print(f"  = {tag}  台账确认，跳过({info})")
                skip += 1
                continue
        if not os.path.isfile(src):
            print(f"  ! {tag}  源文件不存在")
            fails.append((stem, "源文件不存在"))
            fail += 1
            continue
        outdir = safe_dir(stem, i)
        os.makedirs(outdir, exist_ok=True)
        try:
            p = subprocess.run(
                [PY, KU, "-s", src, outdir],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=1800,
            )
            rc = p.returncode
        except Exception as e:
            rc, p = -1, None
            err = str(e)
        cands = [os.path.join(outdir, "mobi8", stem + ".epub"),
                 os.path.join(outdir, "mobi7", stem + ".epub"),
                 os.path.join(outdir, stem + ".epub")]
        eps = [c for c in cands if os.path.isfile(c)]
        if not eps:
            allp = []
            for root, _, files in os.walk(outdir):
                for fn in files:
                    if fn.lower().endswith(".epub"):
                        allp.append(os.path.join(root, fn))
            if allp:
                eps = [max(allp, key=os.path.getmtime)]
        if not eps:
            tail = (p.stderr or "")[-160:] if p is not None else err
            print(f"  ! {tag}  转换失败 rc={rc} {tail}")
            fails.append((stem, f"未产出 EPUB rc={rc}"))
            fail += 1
            continue
        good, info = validate(eps[0], src_size)
        if not good:
            print(f"  ! {tag}  校验不通过: {info}")
            fails.append((stem, f"校验不通过 {info}"))
            fail += 1
            continue
        shutil.copyfile(eps[0], dst)      # 直接覆盖，不做删除操作
        sz = os.path.getsize(dst)
        ledger[stem] = {"size": sz, "src": src_size, "at": RUNID}
        with open(LEDGER, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=1)
        print(f"  + {tag}  {src_size/1048576:.2f}→{sz/1048576:.2f} MB  {info}")
        ok += 1
    dt = time.time() - t0
    print()
    print(f"完成：新转换 {ok} / 台账跳过 {skip} / 失败 {fail}   用时 {dt/60:.1f} 分钟")
    if fails:
        print("失败清单：")
        for n, why in fails:
            print(f"  - {n}: {why}")
    with open(os.path.join(WORKROOT, "_convert_report.json"), "w", encoding="utf-8") as f:
        json.dump({"ok": ok, "skip": skip, "fail": fail, "fails": fails,
                   "runid": RUNID, "out": OUT}, f, ensure_ascii=False, indent=1)
    eps = [x for x in os.listdir(OUT) if x.lower().endswith(".epub")]
    tot = sum(os.path.getsize(os.path.join(OUT, x)) for x in eps)
    print(f"输出目录共 {len(eps)} 个 EPUB，合计 {tot/1048576:.0f} MB")


if __name__ == "__main__":
    main()
