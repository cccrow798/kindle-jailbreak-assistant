# Legacy 机型 LanguageBreak 实战（PW3/G090 等旧机型 + 浏览器越狱失败时）

> 本文来自一次完整的 PW3（Paperwhite 7代，序列号 G090，固件 5.16.2.1.1，soft-float）实战：
> WinterBreak2 反复失败 → 精确诊断 → 改走 LanguageBreak → 一次成功 → 装齐 KOReader + 微信读书（觅阅）。
> 适用场景：**固件 ≤ 5.16.2.1.1 的旧机型**，或任何「WinterBreak2 触发后只提示下载、无任何日志」的设备。

---

## 一、决策树：浏览器越狱失败时怎么办

```
WinterBreak2 点 Jailbreak 后只出现「体验版网页浏览器已成功下载 xxx.mobi」提示、无日志
├─ ① 诊断：浏览器里打开 file:///mnt/us/winterbreak2/dialoger.html（换成诊断页）
│     屏幕打印 typeof nativeBridge
│     ├─ undefined（本地 file:// 页面）→ 再测 http:// 远程页面
│     │    ├─ 远程页面仍 undefined → 【结论】旧浏览器不注入系统接口，
│     │    │   WinterBreak2 在此机型永远无法触发 → 走 LanguageBreak（本文）
│     │    └─ 远程页面有值 → 改用局域网页面直接触发（免恢复出厂，优先！）
│     └─ 有值 → 页面加载正常，问题在脚本拉取环节，见「二、网络坑」
└─ 排除法确认机型路线：
    Véra：仅 KT5/PW5 及更新机型 → PW3 等旧机不可用
    LanguageBreak：≤5.16.2.1.1 任何机型 → 旧机唯一可行路
```

**关键事实（实测确认）**：PW3 的旧版 WebKit（AppleWebKit/534）在 `file://` 和 `http://`
页面中**都不注入 `nativeBridge`**。WinterBreak2 的触发链依赖这个接口，所以在此机型上
「提示已下载」就是终点，重试多少次都一样。不要在重试上浪费时间。

**必须先向用户确认的代价**：LanguageBreak 需要恢复出厂设置。中国区 Kindle 注册通道已关闭，
恢复后设备**无法再注册亚马逊账号**，亚马逊购买的正版书（带 DRM）将无法再读。
动手前：① 完整备份 `documents/`（含 My Clippings.txt 和全部 .sdr）；② 用户明确同意。

---

## 二、网络坑（国内环境几乎必踩）

| 坑 | 事实与对策 |
|----|-----------|
| jb.sh 截断 | `http://kindlemodding.org/jb.sh` 完整大小 **8,691,170 字节**。直连反复断，`curl -C -` 断点续传补全；不完整时解码命令不在文件里，执行后静默失败 |
| GitHub LFS 极慢 | `media.githubusercontent.com` 实测 12KB/s。先调 LFS batch API 拿 S3 直链，仍慢就放弃该通道 |
| ghfast.top 是快通道 | `https://ghfast.top/<原URL>` 对 github release/raw 快 12 倍（40MB 包实测 48 秒）。**所有 GitHub 下载优先走它** |
| 官方 kpkg 下载不动 | KOReader 的 `.kpkg` 是 LFS 存储。绕过方法：直接下载官方 release zip（`koreader-kindlepw2-v<ver>.zip`），手动解压部署，效果相同 |

---

## 三、LanguageBreak 全流程（实测通过版）

材料：`notmarek/LanguageBreak` release 1.0.2.1（`LanguageBreak-16.11.23.tar.gz`，2.5MB）。
README 明确支持 ≤5.16.2.1.1 的任何 Kindle。解压后用 `LanguageBreak/` **里面的内容**平铺投放。

### 阶段 A：进入 demo 模式（设备上操作）

1. 确认无密码锁；搜索框 `;enter_demo` → 回车 → **重启设备**
2. demo 配置向导：跳过 Wi-Fi → 商店信息随便填 → 跳过 payload → demo 类型 **standard** → Done
3. **卡死在「展示机无内容…CONFIGURE DEVICE」待机页**（高发！论坛同款案例 lux1963）：
   - 秘密手势：**两根手指在屏幕右下角快速同时点一下并抬起，紧接着单指从同一角斜向左下角划**。注意是右下角，不是对话框文字行
   - 官方说法「很挑剔（finicky）」：没反应就换节奏（极快/慢速）、换两指间距、短按电源键唤醒后 1 秒内做，多试 5–10 次
   - 实战记录：手势多次失败后**再次触发时成功**，成功后直接可用 `;demo`

### 阶段 B：文件投放 + 触发

4. `;demo` → **Sideload Content** → 数据线连电脑，投放（根目录平铺）：
   - `.demo/boot.flag`（隐藏目录）、`jb`、`patchedUks.sqsh`、`DONT_CHECK_BATTERY`
   - `documents/dictionaries/` 下的 0 字节注入文件（漏洞代码在**文件名**里，勿"修复"大小）
   - `Update_hotfix_languagebreak-zh-Hans-CN.bin`（中文界面热修复，也在包根目录）
   - 拷完 `find /Volumes/Kindle -maxdepth 2 -name "._*" -delete`（macOS AppleDouble 会破坏文件名注入）→ `sync` → 弹出
5. `;demo` → **Resell Device** → Yes/Resell（会清书库，有备份，不怕）
6. ⚡ 出现「press power button to start」→ 长按电源键 → **语言选择菜单 → 简体中文**
7. 屏幕滚日志 = 成功：`LanguageBreak by Marek` → `I am root - uid=0(root)` → `Added developer key :)` → `Finished installing jailbreak`

> 实战记录：Resell 后**第一次投放的文件并未被清除**，即使错过了"第二次拷贝窗口"（USB 在该状态枚举不到设备）漏洞照样触发。赶不上窗口不要慌，直接选语言。

### 阶段 C：持久化收尾

8. 重启进正常模式 → 设置向导点 **Set up later** 一路跳过 → 连电脑
9. 验证：根目录有 `LanguageBreakRan`、`languagebreak_log`；投放 `Update_hotfix_languagebreak-zh-Hans-CN.bin` → 弹出 → 设备上【设置 → 菜单 → 更新您的 Kindle】→ 重启
10. 验证：搜索框 `;log runme` 出现 `No user script found.`；连电脑确认 `libkh`、`mkk`、`rp` 三件套存在
11. 清理可删残留：`languagebreak_log`、`LanguageBreakRan`、`patchedUks.sqsh`
12. **恢复书籍备份**：`cp -R backup/documents/. /Volumes/Kindle/documents/`（实测 Resell 并未清掉 documents，只需补差异）

---

## 四、⚠️ 最大暗坑：必须装 Universal Hotfix，KUAL 才会出现

LanguageBreak 自带热修复只做持久化。**不装 Universal Hotfix 时，`documents/` 里的
`KUAL.jar`/`KUAL.sh` 根本不会在图书馆显示**（表现为"文件都在，图书馆没有 KUAL"）。

1. 下载 `KindleModding/Hotfix` release 的 `Update_hotfix_universal.bin`（3.7MB，走 ghfast）
2. 拷到**根目录**（确认无其他 .bin 干扰）→ 弹出 → 【设置 → 菜单 → 更新您的 Kindle】→ 重启
3. 图书馆出现 **「Run Hotfix」** booklet → 点开运行一次
4. 运行后 `.sh` booklet 环境激活，KUAL 随之显示

启动器选择：现代设备官方推荐 KPM/Jobman（`;kpm`，需 ≥5.16.3 固件栈）；
**旧机（<5.16.3）用 PEKI**（`KindleTweaks/PEKI`，KUAL.jar + KUAL.sh 放 documents 即可，无需 MRPI）。
注意 PEKI 是经典路线，设备栈检查：`libkh/bin/` 里只有 fbink = 经典 MKK 栈，没有 KPM。

---

## 五、KOReader + 微信读书（soft-float 机型 kindlepw2 平台）

| 组件 | 来源与版本 | 部署位置 |
|------|-----------|---------|
| KOReader | 官方 release `koreader-kindlepw2-v2026.07.zip`（40.6MB，走 ghfast） | zip 内 `koreader/` → 根目录；`extensions/koreader/` → `/extensions/` |
| PEKI 启动器 | `KindleTweaks/PEKI` release `PEKI.zip` | `KUAL.jar` + `KUAL.sh` → `/documents/` |
| 觅阅（微信读书） | `miumiupy98-art/miuread-koreader` release v6.2.1（full zip） | `miuread.koplugin/` → `/koreader/plugins/`（要求 KOReader ≥2026.03） |

流程要点：
- 部署后删全部 `._*`，`sync` 后弹出，**重启设备**让图书馆索引 KUAL
- 图书馆 → KUAL → **Start KOReader**（带框架正常启动）→ 首次启动白屏十几秒属正常
- 觅阅入口：KOReader 顶部**扳手图标（工具）** → 觅阅 → 打开书架
- 首次弹「觅阅桌面 vs 插件模式」→ 选**觅阅桌面**（完整书架 UI，无美化冲突时不选插件模式）
- 登录需 Wi-Fi → 微信扫码一次，登录态持久保存
- 退出回 Kindle 主页：觅阅桌面右上 **☰ → 退出 KOReader**（电源键只是休眠）
- 用户提问「我的亚马逊账户是什么」→ 恢复出厂后无从查证也无必要：微信读书/zlib/本地书都不需要亚马逊账号，注册提示一律跳过

---

## 六、z-library 关联（用户实测后暂缓，方案已验证可行）

z-lib **没有官方 OPDS 接口**。社区做法是本机跑桥接服务 + KOReader OPDS 客户端连接：

- **免账号方案**：`Dking08/cOPDSzlib`（Node.js，桥接 libgen.li，无认证无限制）。`npm install && PORT=3000 node server.js`，KOReader OPDS 添加 `http://<Mac局域网IP>:3000/opds`。限制：电脑开机且与 Kindle 同 Wi-Fi
- **z-lib 账号方案**：`octavianx/opds4zlibrary`（Python+Playwright 自动登录提取 cookie），书源为 z-lib 本体
- 长期方案：cOPDSzlib 部署到 Render/Railway 免费层得公网地址
- 若设备有 KPM 栈（≥5.16.3），可 `;kpm install koreader` 一键安装（见 `references/03`）

---

## 七、验收清单（全流程完成标志）

- [ ] `;log runme` → `No user script found.`
- [ ] `libkh` `mkk` `rp` 三件套在根目录
- [ ] 图书馆有「Run Hotfix」且已运行过；有 KUAL
- [ ] KUAL → Start KOReader 能进入 KOReader
- [ ] 觅阅 → 微信书架能拉出书架并下载/阅读，进度与手机同步
- [ ] 原有书籍照常可读，划线摘录（My Clippings.txt）完好
- [ ] 提醒用户：不恢复出厂、不手动升级固件、系统更新已被屏蔽属正常
