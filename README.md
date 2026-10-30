# kindle-jailbreak-assistant · Kindle 越狱与 KOReader 全流程助手

把一台**原厂 Kindle**带到「越狱 + KOReader + 微信读书（觅阅）+ 好词典」的可用状态，覆盖沿途所有已知的坑。

> **v1.1.0 更新**：新增 PW3（Paperwhite 7代/G090，固件 5.16.2.1.1）LanguageBreak 完整实战——
> WinterBreak2 在旧机型上反复失败的精确诊断方法、demo 模式卡死的手势解法、
> Universal Hotfix 暗坑（不装它 KUAL 永远不显示）、KOReader + 微信读书部署清单。

这是一个 [WorkBuddy](https://www.workbuddy.cn) 技能（Skill），解压后放入 `~/.workbuddy/skills/` 即可使用。

---

## 它能做什么

| 场景 | 能力 |
|------|------|
| 越狱决策 | 机型/固件判定 → 自动选择 WinterBreak2 / Sanctuary / Véra / LanguageBreak，附中国区账号限制分析 |
| 越狱执行 | 全流程脚本 + 每一步的屏幕判据（看到什么日志 = 什么状态） |
| 微信读书 | KOReader + 觅阅（miuread）部署，微信扫码登录，书架/进度/划线与手机双向同步 |
| 书籍安全 | 越狱前自动备份 documents（含 My Clippings 划线），生成 CSV/Markdown 台账 |
| 电子书 | AZW3→EPUB 转换、DRM 判定（不破解 DRM）、词典（StarDict）部署 |
| 排错 | 「书不显示」「变卡」「kpm 没反应」「KUAL 不显示」等按症状分类的排错树 |

## 亮点：实测踩坑沉淀（v1.1.0）

- **旧机型浏览器漏洞诊断法**：PW3 的旧版 WebKit 不注入 `nativeBridge`，WinterBreak2 永远无法触发——先探测再决策，不浪费时间重试
- **LanguageBreak 实战全记录**：demo 模式「展示机」卡死的秘密手势（右下角双指点击+斜划）、Resell 后文件残留规律（第二拷贝窗口错过也能成功）
- **Universal Hotfix 暗坑**：LanguageBreak 自带热修复只做持久化；不装通用热修复并运行 Run Hotfix，`documents/` 里的 KUAL 根本不显示
- **国内网络下载经验**：ghfast.top 镜像快 12 倍、jb.sh 完整大小 8,691,170 字节需断点续传、Git LFS 慢通道绕行方案
- **合规红线**：不刷第三方固件、不破解 DRM、恢复出厂的代价（中国区注册通道关闭）事先告知

## 安装

```bash
unzip kindle-jailbreak-assistant.zip -d ~/.workbuddy/skills/
# 重启 WorkBuddy 或重新打开会话即可。触发词：Kindle 越狱 / KOReader / 微信读书 / 觅阅
```

## 使用

在 WorkBuddy 对话里说：

- 「帮我的 Kindle 越狱，装微信读书」
- 「我的 Kindle 是 PW3、固件 5.16.2.1.1，能越狱吗？」
- 「越狱后图书馆里看不到 KUAL 怎么办？」

## 免责声明

- 越狱存在低概率变砖风险，可能失去官方保修；请自担风险
- 本工具不破解任何 DRM；亚马逊购买的正版书在 KOReader 中不可读属正常
- 请遵守你所在地区的法律法规；恢复出厂前务必备份

## 致谢

- 原始技能作者：韦新锋（v1.0.x）
- [KindleModding 社区](https://kindlemodding.org) —— WinterBreak2 / Universal Hotfix / 官方文档
- [notmarek/LanguageBreak](https://github.com/notmarek/LanguageBreak) —— 旧机型越狱方法
- [penguins184 (KindleTweaks)](https://github.com/KindleTweaks) —— PEKI 启动器
- [miumiupy98-art/miuread-koreader](https://github.com/miumiupy98-art/miuread-koreader) —— 微信读书插件
- [koreader/koreader](https://github.com/koreader/koreader) —— 阅读器平台本体
