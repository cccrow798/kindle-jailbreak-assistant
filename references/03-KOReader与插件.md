# 03 · KOReader 与插件（含微信读书、词典）

---

## 一、先认识 KPM 体系

越狱完成后设备上有两样东西：

| 组件 | 作用 |
|------|------|
| **KMC**（`libkh` / `kmc`） | 越狱核心与**包管理器**，提供 `;kpm` 系列命令 |
| **KPM**（Kindle Package Manager） | 安装/启动/卸载第三方包（KOReader、kTerm 等） |

常用命令（在 Kindle **搜索框**里输入）：

| 命令 | 作用 |
|------|------|
| `;kpm update` | 刷新包索引（**验证越狱是否生效的常用手段**） |
| `;kpm install <id>` | 安装包（如 `koreader`） |
| `;kpm launch <id>` | 启动包 |
| `;kpm uninstall <id>` | 卸载包 |
| `;log` | 输出日志，越狱是否生效的标志 |

### 关于 KUAL

官方已说明：过去用 KUAL 通过 scriptlet 启动应用，**"this is now obsolete and does not work"**。
**本技能全程不依赖 KUAL**，入口一律走 `documents/*.sh` scriptlet（由 `sh_integration` 索引成一本"书"）。
部分老机型社区仍在使用 PEKI 版 KUAL，但**不是必需**，不要为了它去改越狱结构。

---

## 二、KOReader 的两种安装方式

### 方式 A：设备在线装（设备能联网时最省事）

搜索框依次执行：

```
;kpm update
;kpm install koreader
```

### 方式 B：电脑离线装（本技能推荐，设备无需联网）

适用场景：设备 Wi-Fi 不稳、不想在设备上开网络、或需要批量部署。
原理：`/mnt/us` 就是 USB 可见分区，**KPM 的路径全部落在这个分区上**，所以电脑可以直接把包装进去。

`.kpkg` 包（本质是 `tar.gz`）的结构与落点：

```
koreader/                → F:\koreader\                （程序本体）
extensions/<id>/         → 仅当设备已有 /mnt/us/extensions 才拷   （KUAL 用，通常跳过）
scriptlets/<Name>.sh     → F:\documents\<Name>.sh       （图书馆入口）
manifest.json / launch.sh / install.sh / uninstall.sh / DO_NOT_EDIT
                         → F:\kmc\kpm\packages\<id>\    （包管理元数据）
```

KPM 内部路径常量：

| 用途 | 路径 |
|------|------|
| 包目录 | `/mnt/us/kmc/kpm/packages` |
| 数据库 | `/mnt/us/kmc/kpm/kpm.db` |
| 临时目录 | `/mnt/us/kmc/kpm/tmp` |

两个关键事实让离线安装可行：

- `launch` 子命令**只检查 `<pkg_path>/<id>/launch.sh` 是否存在**，不查数据库
- 因此**不需要手工造 `kpm.db`**；日后用户真跑 `;kpm install <id>` 会自行注册，且 `install.sh` 是幂等的

**执行**：

```bash
python scripts/fetch_kpm_catalog.py                                   # 看有哪些包与平台
python scripts/fetch_kpm_catalog.py --download koreader --variant kindlepw2 -o ./pkg
python scripts/install_kpm_package.py --drive F: --package ./pkg/koreader_*.kpkg
python scripts/verify_install.py     --drive F: --package ./pkg/koreader_*.kpkg
```

**启动**：安全弹出 → 拔线 → **重启一次 Kindle** → 图书馆点 KOReader；或搜索框 `;kpm launch koreader`。

### 为什么必须重启一次

`documents/*.sh` 要被系统索引成图书馆条目，需要重新扫描；重启是最可靠的触发方式。图标可能延迟出现，再重启一次即可；仍无则在搜索框跑 `;kpm update`。

---

## 三、微信读书（觅阅插件）

**性质**：社区开发的 KOReader 第三方插件（`miuread.koplugin`），对接微信读书服务。**非官方**，接口可用性依赖微信读书，使用时须遵守其用户协议。

**安装**：

1. 解压 `miuread-v<版本>-full.zip` → 得到 `miuread.koplugin` 文件夹
2. **整个文件夹**拷到 `F:\koreader\plugins\`（该目录已存在，内含官方插件）
3. 安全弹出 → 拔线 → 打开 KOReader → 工具菜单 → **觅阅** → 微信扫码登录

**使用要点**：

- 首次加载封面较慢，建议**下载到本地离线读**
- 进度、划线、阅读时长会与手机端**双向同步**
- KOReader 版本要求：**≥ 2026.03**（装之前先确认版本）

---

## 四、词典

### 4.1 KOReader 只认 StarDict

| 项 | 说明 |
|----|------|
| 格式 | **StarDict**：`.ifo` + `.idx` + `.dict` 或 `.dict.dz`（可带 `.syn`） |
| 目录 | `F:\koreader\data\dict\`（设备上即 `/mnt/us/koreader/data/dict`） |
| 扫描方式 | **递归扫描子目录**（`getIfosInDir()`），但跳过 `res/` |
| 额外支持 | 支持包内 `.css` 样式与 `res/` 目录里的图片 |

意味着：**可以按语言分子目录存放**，不影响识别。但**不支持** Kindle 原生的 `.mobi` / `.azw` 词典格式，也无法直接转换（原生词典多为 DRM 保护）。

### 4.2 部署

```bash
python scripts/copy_dict.py --drive F: --source ./dict
python scripts/list_dicts.py --drive F:            # 列出设备上已装词典
python scripts/probe_dict.py --drive F:            # 抽查词条可达性
```

推荐配置（4 本，覆盖四类查询）：

| 类型 | 例子 | 作用 |
|------|------|------|
| 英汉 / 综合 | ECDICT（数百万词条） | 英文单词查中文，覆盖专业词 |
| 英英 | reader.dict EN 类 | 英文释义 + 词形变化 |
| 汉汉 | 汉语词典 | 中文释义 |
| 汉英 | 汉英词典 | 中文查英文 |

### 4.3 词典配多了会卡（重要）

**症状**：点字查词半天没反应、拉顶部栏迟滞。

**根因**：查一个词时 KOReader 会**依次跑一遍所有启用的词典**；而词典查询走的是 `dismissablePopen`，在协程不可用时会**退化成阻塞式 `io.popen`，直接卡住主线程**。
（全树检索该函数，**只有字典模块在调用它**。）

**处理**：

```bash
python scripts/fix_dict_lag.py --drive F:      # 预览
python scripts/fix_dict_lag.py --drive F: --go # 执行
```

该脚本会：

1. 备份 `settings.reader.lua`
2. 在 `dicts_disabled` 里禁用多余的词典（**禁用 ≠ 删除**，文件保留、随时勾回，效果与删除等效）
3. 调整 `dicts_order` 顺序（把最常用的排前面，命中即停）

**手工核对要点**：除了全局的 `settings.reader.lua`，**每本书的 `.sdr/metadata.*.lua` 里还有 `preferred_dictionaries`**，它会**覆盖全局禁用**。只改全局、不改书的配置，卡顿可能依旧。

**经验值**：启用 **3~4 本**；英英类**不要同时开 3 本以上**。

### 4.4 查不到词时

| 现象 | 原因 |
|------|------|
| 英文单词大量查不到 | 英语词典词条太少 → 换 ECDICT 这类大词库 |
| 变形词查不到（如 `running`） | 词典无词形变化表 |
| 中文尚可、英文差 | 缺英英/英汉大词库 |

**词典从哪来**：优先用 KOReader 内置的「Download dictionaries」（工具 → 词典 → 下载），它对接官方清单与镜像；也可自行获取自由许可的大词库。

---

## 五、配置与备份

| 文件 | 内容 | 建议 |
|------|------|------|
| `koreader/settings.reader.lua` | 全局设置（词典启用、排序、预设） | 每次改动前备份为 `settings.reader.lua.bak-<用途>` |
| `koreader/settings/*.lua` | 各类设置 | 同上 |
| `documents/<书名>.sdr/metadata.*.lua` | 单本书的阅读状态与词典偏好 | 保留，不要删 |

> 改配置在 FAT32 上要**先删再写**：`os.remove()` 之后再 `open(...,'wb')`，**不要**用 `os.replace()` 或"临时文件+改名"。

---

## 六、卸载

| 目标 | 做法 |
|------|------|
| 卸载 KOReader | 搜索框 `;kpm uninstall koreader`（**真会删掉程序本体**，慎用） |
| 卸载觅阅 | 删除 `F:\koreader\plugins\miuread.koplugin\` 整个文件夹 |
| 卸载某本词典 | 删对应目录，或只"禁用"（推荐） |

> 只有用户**明确要求卸载**时才执行。日常排错优先"禁用/停用"，不要删。
