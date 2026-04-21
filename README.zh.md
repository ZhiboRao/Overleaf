# Overleaf 客户端

**非官方** 的 [Overleaf](https://cn.overleaf.com/) macOS 原生桌面客户端，基于 **Python 3** + **PySide6 / QtWebEngine** 构建。

> Looking for the English version? See **[README.md](./README.md)**.

---

## 动机

Overleaf 只提供 Web 版，没有桌面客户端。本项目让它像一个真正的 Mac 应用那样运行：独立 Dock 图标、原生菜单栏、键盘快捷键、系统通知、钥匙串保存凭据；同时借助 Qt 下成熟的 Chromium 内核复用 Overleaf 的所有功能。

## 特性

- **登录持久化**：Cookie 存放在 QtWebEngine Profile 中；邮箱 / 密码可选通过 **macOS 钥匙串** 加密保存（不会明文落盘）。钥匙串后端改用 `/usr/bin/security` 命令行调用，因而在未签名的 `py2app` 产物中也能正常读写。
- **原生菜单栏** 遵循 Mac 习惯：
  - `⌘R` 刷新
  - `⌘,` 偏好设置
  - `⌘Q` 退出
  - Overleaf 自带的编辑器快捷键（`⌘↩` 触发编译等）继续可用。
- **窗口内工具栏**：Back / Forward / Reload / Home / Downloads，字号放大，工具栏高度可在偏好设置中自定义。
- **关闭只是隐藏**（参考 Claude Desktop / Slack）：点击红色关闭按钮只会隐藏主窗口，应用仍在后台运行；点击 Dock 图标即可唤回窗口。`⌘Q` 仍可真正退出。
- **下载面板**：与偏好设置共用同款"页式"窗框（大标题 + 副标题、SECTION 分组标签、分隔线、提示、底部按钮行），内部以 Motrix 风格卡片列出进行中与已完成下载，带彩色文件类型徽标、实时速度 / 剩余时间、进度条、`Cancel` 与 `Show in Finder` 按钮。
- **中英双语 UI**：偏好设置里单一的 **语言** 选项（`自动`（跟随系统）/ `English` / `中文`）会即时重译工具栏、菜单、偏好设置与下载面板，无需重启；同一选项也决定访问哪个 Overleaf 镜像（`www` ↔ `cn`）。
- **现代全局样式表**：单一参数化 QSS 驱动整个应用，标题 / 分组 / Tab / 下载卡片等尺寸皆围绕一个基准字号同比缩放，视觉比例始终协调。
- **外观设置**：在偏好设置里可以调节：
  - 基准字号（12–24 pt，实时生效）
  - 偏好设置 / 下载面板的窗口透明度（50–100 %，拖动时即时预览）
  - 工具栏行高（内边距 2–14 px）
- **状态栏时钟与工作计时**：状态栏右侧显示当前时间和本次会话的"实际工作时长"。当窗口被隐藏、失去前台焦点，或连续 2 分钟没有键鼠 / 触控板输入时计时自动暂停；一旦重新有输入立即恢复。空闲检测通过 `ctypes` 直接调用 macOS 的 `CGEventSourceSecondsSinceLastEventType`，不引入额外依赖。
- **系统通知**：通过 `osascript` 调用通知中心，失败回退到 Qt 系统托盘通知。
- **Dock 徽标**：使用 `NSApp.dockTile` 在离线等状态下显示 `!`。
- **离线检测**：每 30 秒向首页做一次 HEAD 探测，校园网强制门户 / DNS 故障也能即时在状态栏和通知中显示。
- **一键安装**（`install.sh`）：venv → py2app → 拷贝到 `/Applications`。构建产物可用 `./clean.sh` 清理（加 `--deep` 连 `.venv/` 一起删）。
- **偏好设置**：iTerm2 风格的横向 Tab 布局；可修改首页地址、缩放比例、**语言**（`自动` / `English` / `中文`，同时决定界面文本与 Overleaf 镜像）、下载目录，并切换通知 / Dock 徽标 / 钥匙串自动保存。
- **多窗口**：支持 `target="_blank"` 链接在应用内另开窗口。
- **macOS 模板图标**：1024×1024 画布内的圆角方块约占 80%，四周留透明边距，Dock 中的视觉大小与系统自带 app 保持一致。
- **清晰分层架构**：`core/`（与 UI 无关）、`ui/`（Qt）、`platforms/mac/`（macOS 集成）。

## 环境要求

- macOS 11（Big Sur）或更高版本
- Python ≥ 3.10
- Xcode 命令行工具（`sips` / `iconutil` 用于重新生成图标）
- 可选：通过 `brew install create-dmg` 安装 [`create-dmg`](https://github.com/create-dmg/create-dmg)，用于构建 DMG

## 安装

### 一键安装（推荐）

```bash
git clone git@github.com:ZhiboRao/Overleaf.git
cd Overleaf
./install.sh
```

该脚本会创建 `.venv/`、安装依赖、使用 py2app 构建 `.app`，并将其复制到 `/Applications/Overleaf Client.app`；如果已经安装 `create-dmg`，还会在 `dist/` 下生成 DMG。

### 从源码运行（开发模式）

```bash
make install-dev
make run
```

### 常用 make 目标

| 目标 | 说明 |
|---|---|
| `make run` | 以源码方式运行（在 `.venv` 中） |
| `make lint` | 运行 `ruff` + `mypy` |
| `make icon` | 重新生成 `resources/icon.icns` |
| `make app` | 仅构建 `.app` |
| `make dmg` | 构建发布用 DMG |
| `make clean` | 清理构建产物 |
| `make distclean` | 同时删除 `.venv/` |

## 架构

```
src/overleaf_client/
├── app.py              # 组合入口
├── core/
│   ├── config.py       # AppConfig 与 JSON 持久化
│   ├── credentials.py  # 钥匙串凭据存取
│   ├── i18n.py         # 界面文案字典与当前语言切换
│   ├── network.py      # 网络可达性监测
│   └── browser.py      # QtWebEngine Profile / Page
├── ui/
│   ├── main_window.py  # 主窗口
│   ├── menu_bar.py     # 原生菜单构造
│   ├── shortcuts.py    # 注入 Overleaf DOM 的 JS 片段
│   ├── notifications.py# osascript + 托盘通知兜底
│   ├── downloads.py    # 下载面板（偏好设置同款页式窗框 + Motrix 风格卡片）
│   ├── styles.py       # 全局参数化 QSS 样式表
│   └── preferences.py  # iTerm 风格 Tab 布局的偏好设置对话框
└── platforms/mac/
    ├── dock.py         # Dock 徽标助手
    └── idle.py         # CoreGraphics 系统空闲检测（ctypes）
```

三层之间严格单向依赖：`app.py` 负责组装；UI 依赖 core；`platforms/mac` 可选且从不被 `core/` 反向依赖。

## 数据位置

| 内容 | 路径 |
|---|---|
| 设置 JSON | `~/Library/Application Support/Overleaf Client/settings.json` |
| Cookie / 缓存 / localStorage | `~/Library/Application Support/Overleaf Client/webengine-profile/` |
| 保存的凭据 | macOS 钥匙串，服务名 `com.zhiborao.overleafclient` |
| 下载文件 | `~/Downloads`（可配置） |

## 隐私与安全

- 密码通过 `/usr/bin/security` 写入系统钥匙串，不会明文落盘，也不会在除 HTTPS 登录请求之外的任何位置发送。
- Cookie 位于 QtWebEngine 沙箱 Profile 目录内。
- 无埋点、无后台回传。网络流量仅来自 Overleaf 本身 + 一个周期性 HEAD 请求（用于离线检测）。

## 免责声明

这是一个 **非官方** 的套壳客户端。"Overleaf" 是 Overleaf / Digital Science 的商标；本项目与 Overleaf 没有任何从属 / 授权 / 赞助关系。使用本客户端仍需遵守 Overleaf 的服务条款。

## 许可证

[MIT](./LICENSE)
