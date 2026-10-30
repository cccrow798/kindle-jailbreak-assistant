---
name: kindle-weread-unlocker
display_name: 墨水屏自由读：Kindle 越狱装微信读书
display_name_en: E-ink Freedom: Kindle Jailbreak for WeRead
category: 效率工具
version: 1.1.0
author: 白马非马（基于韦新锋 v1.0.x 增强更新）
description: Kindle 越狱与 KOReader 全流程助手。当用户想给自己的 Kindle 越狱、装 KOReader、装微信读书（觅阅插件）、换词典、把 AZW3/KFX 转成可读格式，或排查越狱后的问题（书不显示、设备卡顿、启动失败、kpkg 装不上）时使用。覆盖机型与固件判定、WinterBreak2/WinterBreak/SpringBreak 越狱方式选择、KPM 包离线安装、StarDict 词典部署、AZW3 转 EPUB、设备清理与性能归因。触发词：Kindle 越狱、Kindle 刷机、jailbreak、WinterBreak、KOReader、kpm、kpkg、微信读书、觅阅、azw3 转 epub、Kindle 卡顿、Kindle 变砖。
description_zh: 面向 Kindle 用户的一站式越狱与增强助手：先判定机型与固件选出正确的越狱方式，再完成越狱、持久化、离线安装 KOReader 与插件（含微信读书）、部署词典、转换电子书格式、清理设备并归因性能问题，全流程附带可执行脚本与验收标准。
description_en: An end-to-end Kindle jailbreak and enhancement assistant. It identifies the device model and firmware to pick the right jailbreak path, then performs jailbreak, persistence, offline KOReader and plugin installation (including WeRead), dictionary deployment, ebook format conversion, device cleanup, and performance root-causing, with runnable scripts and acceptance checks.
agent_created: true
---

# Kindle 刷机助手

把一台**原厂 Kindle** 带到「越狱 + KOReader + 微信读书 + 好用的词典 + 能读 AZW3」的可用状态，并覆盖沿途所有已知的坑。

**不做的事**：不更换系统、不刷第三方固件、不破解任何 DRM。越狱只解锁设备本身的软件安装权限，原 Kindle 界面和书库照常保留。

---

## 一、何时使用本技能

| 用户的话 | 入口 |
|----------|------|
| 「帮我给 Kindle 越狱 / 刷机」「Kindle 能装 KOReader 吗」 | → 走**阶段 0~6 全流程** |
| 「WinterBreak2 点了没反应 / 只提示下载」「旧机型（PW3 等）越狱」「越狱后图书馆看不到 KUAL」 | → 读 `references/08-Legacy机型LanguageBreak实战.md` |
| 「已越狱，怎么装 KOReader」 | → 跳到**阶段 4** |
| 「KOReader 里看不到我的书」「azw3/kfx 打不开」 | → 跳到**阶段 5.3**，读 `references/04` |
| 「Kindle 变卡了 / 翻页慢 / 查词没反应」 | → 跳到**阶段 6**，读 `references/05` |
| 「想用 Kindle 看微信读书」 | → **阶段 5.1**，读 `references/03` |
| 「越狱后图标不见了 / kpm 命令没反应」 | → 跳到**排错速查**，读 `references/06` |

**开始前必读** `references/07-风险与合规.md`，并把风险如实告知用户，取得同意后再动手。

---

## 二、铁律（违反会变砖或丢数据）

1. **越狱完成后绝不恢复出厂设置**。越狱后恢复出厂 = 越狱失效 + 书库清空。（唯一例外：LanguageBreak 流程**开始前**的恢复出厂是必要环节——那是触发漏洞的方式，且必须先备份并取得用户对"亚马逊正版书不可再读"代价的明确同意，见 `references/08`。）
2. **绝不删除** `libkh`、`kmc`、`koreader`、`apps`、`mesquito`、`documents/*.sh` 这些目录/文件——它们是越狱与启动入口的载体。
3. **不碰 DRM**。遇到 `encryption=2`（Mobipocket DRM）或 KFX（文件头 `DRMION`）的书，**只说明原因，不转换**。这些书在原生阅读器里照常可读。
4. **越狱完成后必须清掉 Kindle 根目录下的 `update*.bin` / `update.bin.tmp.partial`**，并确认系统更新已被屏蔽。
5. **动手前先让用户把 `documents/` 复制一份到电脑**。设备端没有回收站，删了不可逆。
6. **电量 ≥ 50%**，越狱全程不要拔数据线、不要合盖断电。
7. **中国区账号用户注意**：2023 年中国 Kindle 书店停运，主页没有商店入口，**一切依赖商店页面的方法（WinterBreak、SpringBreak）都走不通**，必须选**浏览器触发类**方法（WinterBreak2 / Sanctuary / Véra，均不需要注册亚马逊账号）。
8. **架构必须匹配**：固件 **5.16.3 及以后是 hard-float**，**5.16.2.1.1 及以前是 soft-float**。同一机型若架构不同，扩展包不能互换——装错会直接不能用。

---

## 三、总流程

```
阶段 0  准备        备份 documents、确认电量、关闭飞行模式、开启「显示隐藏项目」
   ↓
阶段 1  识别设备    机型 / 固件 / 账号区域 / 当前是否已越狱      [scripts/detect_kindle.py]
   ↓
阶段 2  越狱        按机型+固件选定方法（先跑官方向导）           [references/01 02]
   ↓
阶段 3  持久化      确认热修复已装（WinterBreak2 自动完成）+ 清 .bin  [references/02]
   ↓
阶段 4  装 KOReader  取官方 KPM 包 → 离线落盘 → 逐文件校验      [scripts/fetch_kpm_catalog.py
                                                                install_kpm_package.py
                                                                verify_install.py]
   ↓
阶段 5  可选增强    5.1 微信读书（觅阅） 5.2 词典 5.3 格式转换    [references/03 04]
   ↓
阶段 6  收尾        清理垃圾 + 性能归因 + 验收清单               [scripts/clean_device.py]
```

---

## 四、分阶段使用方法

### 阶段 0 · 准备

向用户确认并以清单形式回报：

- Kindle 通过 USB 连上电脑，出现盘符（下文统一用 `F:` 指代，用 `ls /f/` 确认实际盘符）
- `documents/` 已备份到电脑（没有就先备份）
- 电量 ≥ 50%
- 已关闭飞行模式、已连上可上网的 Wi-Fi
- Windows 资源管理器已开启「显示隐藏项目」

### 阶段 1 · 识别设备

```bash
python scripts/detect_kindle.py F:
```

脚本只读，输出：机型代号、固件版本、可用空间、是否已越狱（查 `libkh/` 与 `documents/JAILBROKEN.txt`）、已装组件（`koreader/`、`kmc/`）、词典数量、`documents/` 内的书与 `.sdr` 统计。

**据机型与固件决定越狱方式。先跑官方向导**（<https://kindlemodding.org/jailbreak-wizard>，输入序列号前缀 + 固件版本，它会直接给出唯一正确的方法），再对照下表理解取舍：

| 固件区间 | 可用方法 | 触发方式 | 是否需商店/账号 |
|----------|----------|----------|-----------------|
| **≤ 5.16.2.1.1** | **WinterBreak2**（首选）；LanguageBreak（需恢复出厂，≤5.16.2.1.1，PW3/KT4 等旧 soft-float 机型的可靠兜底） | 体验版网页浏览器访问 `penguins184.xyz/wb2` | **不需要**（中国区可用）|
| 5.16.4 – 5.18.3 | **Sanctuary**（首选，浏览器内完成）；Nosebleed（部分机型，5.16.4–5.18.6） | 浏览器访问 Sanctuary 页并先跑兼容性自检 | **不需要**，且支持黑名单/未注册设备 |
| < 5.18.1 | WinterBreak（原版） | 商店页面 | **需要**商店 → 中国区不可用 |
| 5.18.1 – 5.18.5 | AdBreak（**仅广告版** Kindle，且不能去掉广告） | 广告相关漏洞 | 需要 |
| 5.18.1.1.1 / 5.19.2(.0.1) | SpringBreak | **电脑端工具**（Win/macOS/Linux 可执行文件） | **需要**商店 → 中国区不可用 |
| ≤ 5.19.6 | Véra（2026-08 发布，字体解析漏洞，覆盖面最广） | 见官方向导 | 不需要 |
| 高于上述上限 | **暂无公开方法** | — | — |

> 上表整理于 **2026-09**。固件区间与方法是**动态变化**的（Amazon 会修补漏洞，社区会出新方法），**每次都必须以官方向导的实时判定为准**，不要把本表当作长期事实。
> 判断架构：`5.16.3` 起为 hard-float，`5.16.2.1.1` 及以前为 soft-float —— 决定后续装哪个平台的包。
> 完整对照与取舍说明见 `references/01-机型判定与越狱方式.md`。

### 阶段 2 · 越狱

按上表选定方式后，**逐步照做**，不要跳步。WinterBreak2 的完整操作（含屏幕上应出现的每一行日志、如何判断成功）见 `references/02-越狱实操.md`。

**WinterBreak2 触发失败的诊断与兜底**：若点 Jailbreak 后只出现「已成功下载 xxx.mobi」提示、始终无日志，先按 `references/08-Legacy机型LanguageBreak实战.md` 第一节的诊断树定位（老机型浏览器可能根本不注入 `nativeBridge`，重试无意义）；确认是机型限制后走 LanguageBreak 路线。该文档含 PW3 实测全流程：demo 模式卡死的手势解法、Resell 投放时机、Universal Hotfix 必装（否则 KUAL 不显示）、KOReader+觅阅部署清单。

关键节点：

1. 解压对应压缩包，把整个文件夹拷到 **`F:\` 根目录**
2. 安全弹出 → 在 Kindle 上打开「体验版网页浏览器」→ 访问触发地址 → 点执行按钮
3. 屏幕会刷日志，最后出现 `Restarting GUI / Please Wait...`，**中途弹出「应用程序错误」是正常的，点关闭继续等**
4. 系统界面自动重启（看起来像卡住，属正常）

### 阶段 3 · 持久化

- WinterBreak2 / SpringBreak / Sanctuary 会**自动装好热修复并屏蔽系统更新**，不需要再手动跑 hotfix。
- 但**必须**删除 Kindle 根目录下所有 `update*.bin`、`update.bin.tmp.partial`。
- 验收：重启一次 Kindle，`documents/JAILBROKEN.txt` 仍在、搜索框输入 `;kpm update` 有反应 → 越狱稳定。

### 阶段 4 · 安装 KOReader（离线方式，不依赖设备联网）

**先取消 KUAL**：官方已明确 KUAL「is now obsolete and does not work」，不要再装 KUAL / MRPI，入口一律走 `documents/*.sh` scriptlet。

```bash
# ① 查官方仓库里当前可用的包（自动识别 Git LFS，列出平台后缀与 SHA256）
python scripts/fetch_kpm_catalog.py

# ② 下载（老机型用 kindlepw2 后缀，新机型用 kindlehf，二者不可混用）
python scripts/fetch_kpm_catalog.py --download koreader --variant kindlepw2 -o ./pkg

# ③ 先预览落盘计划（默认只预览，不写设备）
python scripts/install_kpm_package.py --drive F: --package ./pkg/koreader_2026.7.2_kindlepw2.kpkg

# ④ 确认后执行（约 1000 文件 / 85MB，请用后台执行）
python scripts/install_kpm_package.py --drive F: --package ./pkg/koreader_2026.7.2_kindlepw2.kpkg --go

# ⑤ 逐文件校验（SHA256 全比对，0 不一致 / 0 缺失才算通过）
python scripts/verify_install.py --drive F: --package ./pkg/koreader_2026.7.2_kindlepw2.kpkg
```

落盘位置（与设备上执行 `;kpm install koreader` 完全一致）：

| 内容 | 位置 |
|------|------|
| 程序本体 | `F:\koreader\` |
| 图书馆入口 scriptlet | `F:\documents\KOReader.sh` |
| 包管理元数据 | `F:\kmc\kpm\packages\koreader\` |
| KUAL 用的 `extensions/` | **故意跳过**（本机无 `/mnt/us/extensions`） |

启动：安全弹出 → 拔线 → **重启一次 Kindle** → 图书馆点 KOReader 图标；或在搜索框输入 `;kpm launch koreader`。

### 阶段 5 · 可选增强

**5.1 微信读书（觅阅插件）** —— 见 `references/03`

把 `miuread.koplugin` 整个文件夹拷到 `F:\koreader\plugins\`，重启 KOReader → 工具菜单 → 觅阅 → 扫码登录。
注意：属社区非官方插件，接口可用性依赖微信读书服务，需遵守其用户协议。

**5.2 词典** —— 见 `references/03`

KOReader 只认 **StarDict** 格式（`.ifo` + `.idx` + `.dict`/`.dict.dz`），且会**递归扫描** `koreader/data/dict` 的子目录。

```bash
python scripts/copy_dict.py --drive F: --source ./dict      # 部署词典
python scripts/fix_dict_lag.py --drive F:                   # 卡顿时诊断（默认只预览）
python scripts/fix_dict_lag.py --drive F: --go              # 确认后精简（禁用多余的，不删文件）
```

**词典保持 3~4 本**（英汉 / 英英 / 汉汉 / 汉英各一）。开 9 本会让查词阻塞主线程，表现为「点字半天没反应」。

**5.3 电子书格式兼容** —— 见 `references/04`

关键结论：**KOReader 不认 `.azw3` 和 `.kfx`**（后缀未在格式注册表里登记，文件浏览器会直接过滤掉，不是文件坏了）。

```bash
python scripts/fetch_kindleunpack.py           # 一次性：取回解封装工具到 ./tools/
python scripts/scan_ebooks.py  F:/documents    # 体检：识别格式/压缩/是否 DRM
python scripts/convert_azw3.py F:/documents    # 无 DRM 的 azw3 → epub（只解封装，不解密）
python scripts/copy_epub.py    --drive F:      # 拷入设备（只创建新文件）
python scripts/verify_epub.py  --drive F:      # 复核：存在性 + 字节数 + MD5 + zip 结构
```

`.pdf`、`.mobi`、`.azw`、`.txt` 都**直接支持**，不要多此一举去转换。

### 阶段 6 · 收尾

```bash
python scripts/clean_device.py F:          # 预览，不删任何东西
python scripts/clean_device.py F: --go     # 确认后再执行
```

清理前必须做三件事：列白名单（只允许删 `documents/` 与 `koreader/data/dict/` 内）、逐文件 MD5 比对电脑备份、把含 `metadata.*.lua` / `*.mbp1` 的 `.sdr` 排除在删除清单外。

**性能归因**（用户说「变慢了」时，别顺着假设答）：

- **文件数量不是性能因素**——打开一本书只加载那一本，100 本和 500 本翻页一样快
- 真正的原因按此顺序查：① 词典启用过多（查 `crash.log` 里 `unwrapped dismissablePopen`）；② 首次打开某本书慢一两秒 = 生成排版缓存，正常；③ 首进文件浏览器慢 = 提取封面，一次性；④ 磁盘剩余空间紧 = 只影响写入，与阅读无关

---

## 五、注意事项（硬性）

| 事项 | 说明 |
|------|------|
| **设备写入规则（FAT32）** | **新建 / 删除可以；覆盖已有文件 / 改名不行**。`os.replace()` 会报 `WinError 5 拒绝访问`，**不要**用「临时文件 + 改名」的套路；覆盖要先 `rm` 再写 |
| **删除需在沙箱外执行** | 沙箱内删除会走回收站逻辑，而 FAT32 没有回收站 → 必然失败 |
| **写大量文件用后台执行** | KOReader 约 1035 文件 / 83MB，USB 约 90 秒，前台会超时被打断，留下截断文件 |
| **`.sdr` 目录不要删** | 里面是阅读进度 / 标注 / X-Ray / 生词本，删了永久丢失（电脑备份里通常没有） |
| **`documents/*.sh` 不要删** | 是 KPM 的 scriptlet 启动器，图标 base64 内嵌在脚本里，删了原生书库就没有 KOReader 入口 |
| **改配置前先备份** | `settings.reader.lua`、每本书的 `metadata.*.lua` |
| **每次改动后重启 KOReader** | 词典列表与文件列表都是启动时扫描的 |
| **包平台后缀不能混用** | 老机型（PW1-3、KT2/3、K4/K5）= `kindlepw2`；新机型（PW4+、KO、Scribe）= `kindlehf` |
| **GitHub 大文件走 media 地址** | `packages/*/artifacts/*.kpkg` 走 Git LFS，用 raw/jsDelivr 只能拿到 133 字节的指针文本 |

---

## 六、排错速查

| 症状 | 首查项 |
|------|--------|
| 浏览器打不开越狱触发页 | Wi-Fi 是否可用；地址是否输错；重启 Kindle 再试 |
| 点越狱按钮没反应 | `F:\winterbreak2\` 文件夹是否存在且完整 |
| 图书馆里没有 KOReader 图标 | scriptlet 未索引 → 再重启一次；仍无则搜索框跑 `;kpm update` |
| `;kpm` 命令没反应 | 越狱持久化失效 → 参照 `references/02` 重跑热修复 |
| KOReader 里看不到某些书 | 九成是 `.azw3` / `.kfx` 被格式过滤 → `references/04` |
| 打开书报错 | 先看该书 `.sdr/` 下有没有 `metadata.*.lua`——没有说明从未成功打开过 |
| 点词查不动、顶部栏迟滞 | 词典开太多 → `scripts/fix_dict_lag.py` |
| 设备整体卡死 | 长按电源键 40 秒强制重启 |

完整排错见 `references/06-排错与FAQ.md`。

---

## 七、参考资料索引

| 文件 | 内容 |
|------|------|
| `references/08-Legacy机型LanguageBreak实战.md` | PW3 实测：WinterBreak2 失败诊断树、LanguageBreak 全流程（含 demo 手势与 Resell 时机）、Universal Hotfix 暗坑、KOReader+觅阅部署清单、zlib OPDS 桥接方案 |
| `references/01-机型判定与越狱方式.md` | 机型代号对照、固件区间、三种越狱方式的适用条件与取舍 |
| `references/02-越狱实操.md` | WinterBreak2 逐步操作、成功判据、持久化与热修复 |
| `references/03-KOReader与插件.md` | KPM 包结构、离线安装原理、微信读书、词典部署与调优 |
| `references/04-电子书格式与转换.md` | KOReader 格式注册表、AZW3→EPUB 流程、DRM 判定与拒绝口径 |
| `references/05-性能与清理.md` | 「变慢」的归因链、可删/禁删清单、清理执行规则 |
| `references/06-排错与FAQ.md` | 按症状分类的排错树 |
| `references/07-风险与合规.md` | 变砖风险、保修、法律边界、必须向用户告知的内容 |

## 八、脚本索引

所有脚本**默认只读或只预览**，破坏性/写入类操作必须显式加 `--go`。
脚本之间通过工作目录共享台账（默认 `./kindle_work`，可用环境变量 `KINDLE_JB_WORK` 改）。

| 脚本 | 作用 | 写设备 |
|------|------|--------|
| `detect_kindle.py` | 设备体检：固件/架构/越狱状态/组件/词典/书籍统计 | 否 |
| `fetch_kpm_catalog.py` | 列出与下载官方 KPM 包（处理 Git LFS + SHA256 校验） | 否 |
| `install_kpm_package.py` | 按 install.sh 规则离线落盘 | `--go` |
| `verify_install.py` | 逐文件 SHA256 复核安装结果 | 否 |
| `copy_dict.py` | 部署 StarDict 词典（含 res/），逐文件 MD5 校验 | 写入 |
| `fix_dict_lag.py` | 诊断并修复「词典过多导致查词卡顿」 | `--go` |
| `list_dicts.py` | 解析 KOReader 内置词典清单，按语言对列出可下载词典 | 否 |
| `probe_dict.py` | 抽查词典：词条数、变形表、指定词能否查到 | 否 |
| `scan_ebooks.py` | 扫书：格式/压缩/是否加密（**只读文件头，不解密**） | 否 |
| `fetch_kindleunpack.py` | 取回 KindleUnpack 解封装工具（GPL，按需下载，不随技能内置） | 下载到本地 |
| `convert_azw3.py` | 批量 AZW3→EPUB（三重校验 + 台账 + 隔离工作目录） | 否 |
| `copy_epub.py` | 按台账把 EPUB 拷入设备，只创建新文件 | 写入 |
| `verify_epub.py` | 复核设备端 EPUB：存在性 + 字节数 + MD5 + zip 结构 | 否 |
| `clean_device.py` | 清理垃圾（白名单 + 预览 + 清单存档） | `--go` |

> `convert_azw3.py` 需要 **KindleUnpack**（GPL，纯 Python，不涉及解密）。
> 先跑 `fetch_kindleunpack.py` 取回；它会自动发现，也可用环境变量指定：
> `KINDLEUNPACK=/path/to/kindleunpack.py`。

## 九、官方与社区资源

- 越狱向导（按机型固件给出判定）：https://kindlemodding.org/jailbreak-wizard
- WinterBreak2：https://kindlemodding.org/jailbreaking/WinterBreak2/
- 装 KOReader：https://kindlemodding.org/jailbreaking/whats-next/getting-koreader/
- 官方 KPM 包仓库：https://github.com/KindleModding/repo
- KOReader：https://github.com/koreader/koreader
- KindleUnpack：https://github.com/kevinhendricks/KindleUnpack

> 文档站点是 JS 渲染，`WebFetch` 抓不到正文。取源仓库 markdown：
> `https://cdn.jsdelivr.net/gh/KindleModding/kindlemodding.github.io@main/content/<路径>.md`

## 十、执行环境约定

- Python 用托管解释器绝对路径，并设置 `PYTHONIOENCODING=utf-8`（中文书名/文件名多）
- **工作目录设在技能目录之外**（默认是 `./kindle_work`，可用环境变量 `KINDLE_JB_WORK` 改）。
  转换脚本会往里写台账（`_ebook_scan.json` / `_converted_ok.json`）和产物（`epub_out/`），
  提示词里给用户的示例建议用桌面或项目目录，**不要留在 `skills/` 里面**。
- 设备端删除、覆盖、改名必须用 `dangerouslyDisableSandbox` 在沙箱外执行
- 大批量写入、下载、转换用 `run_in_background`
- 所有脚本默认**只读/预览**，破坏性操作必须显式加 `--go` 之类的开关
- 台账（`_converted_ok.json`）一旦校验逻辑有改动，必须删掉重转，否则会沿用旧判定
