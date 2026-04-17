# Overleaf 客户端

**非官方** 的 [Overleaf](https://cn.overleaf.com/) macOS 原生桌面客户端，基于 **Python 3** + **PySide6 / QtWebEngine** 构建。

> Looking for the English version? See **[README.md](./README.md)**.

---

## 动机

Overleaf 只提供 Web 版，没有桌面客户端。本项目让它像一个真正的 Mac 应用那样运行：独立 Dock 图标、原生菜单栏、键盘快捷键、系统通知、钥匙串保存凭据；同时借助 Qt 下成熟的 Chromium 内核复用 Overleaf 的所有功能。

## 特性

- **登录持久化**：Cookie 存放在 QtWebEngine Profile 中；邮箱 / 密码可选通过 **macOS 钥匙串** 加密保存（不会明文落盘）。
- **原生菜单栏** 遵循 Mac 习惯：
  - `⌘S` 触发编译
  - `⌘D` 下载 PDF
  - `⌘N` 新建项目
  - `⌘R` 刷新 / `⌘,` 偏好设置 / `⌘Q` 退出
- **系统通知**：通过 `osascript` 调用通知中心，失败回退到 Qt 系统托盘通知。
- **Dock 徽标**：使用 `NSApp.dockTile` 在离线等状态下显示 `!`。
- **离线检测**：每 30 秒向首页做一次 HEAD 探测，校园网强制门户 / DNS 故障也能即时在状态栏和通知中显示。
- **一键安装**（`install.sh`）：venv → py2app → 拷贝到 `/Applications`。
- **偏好设置**：可修改首页地址、缩放比例、下载目录，并切换通知 / Dock 徽标 / 钥匙串自动保存。
- **多窗口**：支持 `target="_blank"` 链接在应用内另开窗口。
- **清晰分层架构**：`core/`（与 UI 无关）、`ui/`（Qt）、`platform/mac/`（macOS 集成）。

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
│   ├── network.py      # 网络可达性监测
│   └── browser.py      # QtWebEngine Profile / Page
├── ui/
│   ├── main_window.py  # 主窗口
│   ├── menu_bar.py     # 原生菜单构造
│   ├── shortcuts.py    # 注入 Overleaf DOM 的 JS 片段
│   ├── notifications.py# osascript + 托盘通知兜底
│   └── preferences.py  # 偏好设置对话框
└── platform/mac/
    └── dock.py         # Dock 徽标助手
```

三层之间严格单向依赖：`app.py` 负责组装；UI 依赖 core；`platform/mac` 可选且从不被 `core/` 反向依赖。

## 数据位置

| 内容 | 路径 |
|---|---|
| 设置 JSON | `~/Library/Application Support/Overleaf Client/settings.json` |
| Cookie / 缓存 / localStorage | `~/Library/Application Support/Overleaf Client/webengine-profile/` |
| 保存的凭据 | macOS 钥匙串，服务名 `com.zhiborao.overleafclient` |
| 下载文件 | `~/Downloads`（可配置） |

## 隐私与安全

- 密码通过 `keyring` 写入系统钥匙串，不会明文落盘，也不会在除 HTTPS 登录请求之外的任何位置发送。
- Cookie 位于 QtWebEngine 沙箱 Profile 目录内。
- 无埋点、无后台回传。网络流量仅来自 Overleaf 本身 + 一个周期性 HEAD 请求（用于离线检测）。

## 免责声明

这是一个 **非官方** 的套壳客户端。"Overleaf" 是 Overleaf / Digital Science 的商标；本项目与 Overleaf 没有任何从属 / 授权 / 赞助关系。使用本客户端仍需遵守 Overleaf 的服务条款。

## 许可证

[MIT](./LICENSE)
