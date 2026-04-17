#!/usr/bin/env python3
"""Render ``resources/icon.png`` as a macOS-style rounded-square app icon.

将 ``resources/icon.png`` 渲染为 macOS 风格圆角矩形应用图标。

- Canvas: 1024×1024 (the standard macOS icon template).
- Rounded-corner radius: 22.37% of the canvas (matches Big Sur+ apps).
- Background: Overleaf brand green with the transparent logo composited on
  top inside Apple's recommended ~83% safe-area box.

- 画布：1024×1024（macOS 标准模板）。
- 圆角半径：22.37% 画布宽度（与 Big Sur 之后系统一致）。
- 背景：Overleaf 品牌绿；透明 logo 合成在 Apple 推荐 83% 安全区内。

The script reads ``resources/logo.png`` (the original transparent artwork)
and writes ``resources/icon.png`` (the framed app icon). Run
``scripts/build_icon.py`` afterwards to regenerate ``icon.icns``.

本脚本读取 ``resources/logo.png``（透明原图），输出
``resources/icon.png``（带背景的应用图标）。随后运行
``scripts/build_icon.py`` 生成 ``icon.icns``。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

# Overleaf brand green, sampled from the logo artwork.
# Overleaf 品牌绿，从 logo 中取色。
_BG_COLOR = (19, 119, 58, 255)

_CANVAS = 1024
# Apple's macOS icon template: the visible rounded square is ~824/1024 of
# the canvas, with ~100px transparent margin on every side. Without this
# outer margin the icon looks oversized next to stock apps in the Dock.
# Apple 模板：可见圆角方块约占画布 824/1024，四周留 ~100px 透明边距；
# 没有这层外边距，Dock 里会比系统 app 看上去大一圈。
_TILE_RATIO = 0.8047  # 824/1024
_CORNER_RATIO = 0.2237  # macOS Big Sur+ corner radius relative to the tile.
_SAFE_AREA_RATIO = 0.5  # Logo occupies 512 px — measured within the 1024 canvas.

_RESOURCES = Path(__file__).resolve().parent.parent / "resources"
_LOGO_PATH = _RESOURCES / "logo.png"
_ICON_PATH = _RESOURCES / "icon.png"


def _rounded_rect_mask(size: int, radius: int) -> Image.Image:
    """Return an L-mode mask with the squircle-ish rounded rectangle.

    返回一个 L 模式的圆角矩形蒙版。
    """
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=radius, fill=255,
    )
    return mask


def build_icon() -> Path:
    """Compose the icon and write it to ``icon.png``.

    合成图标并写入 ``icon.png``。

    Returns:
        The path to the rendered icon file.
    """
    if not _LOGO_PATH.exists():
        raise FileNotFoundError(
            f"Missing source logo: {_LOGO_PATH}. "
            "Save the original transparent Overleaf logo there.",
        )

    # The shipped PNG is palette-indexed with a white (not transparent)
    # background. Build the silhouette from pixel darkness instead.
    # 官方 PNG 是调色板索引图，背景是白色而非透明。以像素暗度反推剪影。
    source_rgb = Image.open(_LOGO_PATH).convert("RGB")

    target = int(_CANVAS * _SAFE_AREA_RATIO)
    source_rgb = source_rgb.resize(
        (target, target), Image.Resampling.LANCZOS,
    )

    # Luminance: white → 255, green logo → ~70-100. Invert so logo = opaque,
    # then push through a contrast ramp so the silhouette is crisp (not a
    # washed-out gray) while preserving anti-aliasing at the edges.
    # 亮度：白 → 255，绿 logo → 约 70-100；先翻转使 logo 不透明，再通过
    # 对比度曲线把半透明区拉到纯不透明，保留边缘抗锯齿。
    luminance = source_rgb.convert("L")
    inverted = ImageChops.invert(luminance)

    # Pure green pixels invert to L ~172; white pixels invert to 0. Choose
    # the ramp so green is fully opaque while anti-aliased edges still
    # taper off smoothly.
    # 纯绿反相后 L ≈ 172，白色为 0；映射让 logo 内部满不透明，边缘平滑。
    def _ramp(value: int) -> int:
        low, high = 40, 165
        if value <= low:
            return 0
        if value >= high:
            return 255
        return int((value - low) * 255 / (high - low))

    silhouette_alpha = inverted.point([_ramp(i) for i in range(256)])

    white_layer = Image.new("RGBA", source_rgb.size, (255, 255, 255, 255))
    recolored = Image.new("RGBA", source_rgb.size, (0, 0, 0, 0))
    recolored = Image.composite(white_layer, recolored, silhouette_alpha)

    # Build the green rounded-square tile (smaller than the full canvas), then
    # paste it centered so the transparent margin matches Apple's template.
    # 先绘制小于画布的绿色圆角方块，再居中粘贴，外围保留 Apple 模板要求的
    # 透明边距。
    tile_size = int(_CANVAS * _TILE_RATIO)
    tile = Image.new("RGBA", (tile_size, tile_size), _BG_COLOR)

    logo_offset = ((tile_size - target) // 2, (tile_size - target) // 2)
    tile.alpha_composite(recolored, dest=logo_offset)

    tile_mask = _rounded_rect_mask(tile_size, int(tile_size * _CORNER_RATIO))
    final = Image.new("RGBA", (_CANVAS, _CANVAS), (0, 0, 0, 0))
    tile_pos = ((_CANVAS - tile_size) // 2, (_CANVAS - tile_size) // 2)
    final.paste(tile, tile_pos, mask=tile_mask)

    final.save(_ICON_PATH, format="PNG")
    return _ICON_PATH


def main() -> int:
    """Build ``icon.png`` and print its path."""
    path = build_icon()
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
