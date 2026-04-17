# Makefile - common dev/build targets.
# 常用开发与构建目标。

PY ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PYTHON := $(VENV)/bin/python

APP_NAME := Overleaf Client
APP_BUNDLE := dist/$(APP_NAME).app
DMG := dist/$(APP_NAME).dmg

.PHONY: help venv install install-dev run lint icon app dmg clean distclean

help:
	@echo "Targets / 常用目标:"
	@echo "  make venv        - create .venv / 创建虚拟环境"
	@echo "  make install     - install runtime deps / 安装运行依赖"
	@echo "  make install-dev - install dev+build deps / 安装开发&打包依赖"
	@echo "  make run         - run from source / 源码方式运行"
	@echo "  make lint        - run ruff + mypy / 代码检查"
	@echo "  make icon        - rebuild icon.icns / 重新生成 .icns"
	@echo "  make app         - build .app via py2app / 构建 .app"
	@echo "  make dmg         - build distributable DMG / 构建 DMG"
	@echo "  make clean       - remove build artifacts / 清理构建产物"
	@echo "  make distclean   - clean + remove venv / 彻底清理"

$(VENV)/bin/activate:
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip

venv: $(VENV)/bin/activate

install: venv
	$(PIP) install -e .
	$(PIP) install 'pyobjc-framework-Cocoa>=10.0'

install-dev: venv
	$(PIP) install -e '.[mac,build,dev]'

run: install
	$(PYTHON) -m overleaf_client

lint: install-dev
	$(VENV)/bin/ruff check src scripts setup.py
	$(VENV)/bin/mypy src

icon:
	$(PY) scripts/build_icon.py

app: icon install-dev
	rm -rf build dist
	$(PYTHON) setup.py py2app

dmg: app
	@command -v create-dmg >/dev/null 2>&1 || { \
	  echo "create-dmg not found. Install via 'brew install create-dmg'."; \
	  exit 1; }
	rm -f "$(DMG)"
	create-dmg \
	  --volname "$(APP_NAME)" \
	  --window-pos 200 120 \
	  --window-size 600 380 \
	  --icon-size 128 \
	  --icon "$(APP_NAME).app" 150 180 \
	  --app-drop-link 450 180 \
	  "$(DMG)" "$(APP_BUNDLE)"

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache

distclean: clean
	rm -rf $(VENV)
