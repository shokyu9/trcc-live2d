"""Translate TRCC's Qt widgets, including labels created after startup.

TRCC 9.12.2 already stores a language code and has a Chinese translation table,
but much of its Qt GUI uses literal English widget text. This adapter translates
those widgets in place and follows the existing language setting. It does not
alter device data, editable fields, or the renderer.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QAbstractButton, QComboBox, QGroupBox, QLabel, QLineEdit,
    QMainWindow, QMenu, QTabWidget, QTableWidget, QTreeWidget,
)

from trcc.core.i18n import TRANSLATIONS


EXTRA_ZH: dict[str, str] = {
    "(pick a device above)": "（请先在上方选择设备）",
    "24-hour clock": "24 小时制",
    "A video file, or an http / https / rtsp address": "视频文件或 http / https / rtsp 地址",
    "Active theme:": "当前主题：",
    "Add element…": "添加元素…",
    "Add panel": "添加面板",
    "Any connected LCD, or an LED cooler -- which sends its own colours.": "任意已连接的 LCD 或可独立发光的 LED 水冷。",
    "Advanced": "高级",
    "After 11 seconds above it the panel shows only its overlay, on black, until 11 seconds at or below it.": "高于此值 11 秒后，屏幕只显示黑底叠加层；降回此值或以下 11 秒后恢复。",
    "All categories": "全部分类",
    "Application (all devices)": "应用（所有设备）",
    "Apply": "应用",
    "Apply colour": "应用颜色",
    "Bind selected row": "绑定选中行",
    "Brightness:": "亮度：",
    "Brightness pulses up and down at a steady rate.": "亮度以固定速度周期变化。",
    "Browse…": "浏览…",
    "Carousel": "轮播",
    "Colour follows CPU or GPU load (pick the source on the Advanced tab).": "颜色跟随 CPU 或 GPU 负载（在“高级”页选择来源）。",
    "Colour follows CPU or GPU temperature (pick the source on the Advanced tab).": "颜色跟随 CPU 或 GPU 温度（在“高级”页选择来源）。",
    "Colours": "颜色",
    "Corner:": "角落：",
    "Category:": "分类：",
    "Check for updates": "检查更新",
    "Checking for updates…": "正在检查更新…",
    "Choose region…": "选择区域…",
    "Clip in:": "片段起点：",
    "Clip out:": "片段终点：",
    "Clock + calendar (LC2)": "时钟与日历（LC2）",
    "Clock format (every clock):": "时钟格式（全部时钟）：",
    "Clock source:": "时钟来源：",
    "Close media player": "关闭媒体播放器",
    "Color (when mode = Solid):": "颜色（常亮模式）：",
    "Color:": "颜色：",
    "Cloud themes": "云端主题",
    "Configuration": "设置",
    "Connect": "连接",
    "Create from image…": "从图片创建…",
    "Create from video…": "从视频创建…",
    "Crop image": "裁剪图片",
    "Crop video → Theme.zt": "裁剪视频并生成 Theme.zt",
    "Current state": "当前状态",
    "Dashboard layout": "仪表盘布局",
    "Cursor:": "光标：",
    "Cycle through 4 reference colours (test mode)": "循环显示四种参考颜色（测试模式）",
    "DDR multiplier:": "DDR 倍频：",
    "Date format (every date):": "日期格式（全部日期）：",
    "Date format:": "日期格式：",
    "Delete…": "删除…",
    "Device:": "设备：",
    "Device key:": "设备键：",
    "Diagnostic": "诊断",
    "Disconnect": "断开连接",
    "Disk sensor:": "硬盘传感器：",
    "Direction": "方向",
    "Down": "向下",
    "Drawn by TRCC from the effect's settings -- the stick runs it itself, so yours may differ in detail.": "TRCC 根据效果设置绘制预览；灯条自行运行效果，实际画面可能略有差异。",
    "Display": "屏幕设置",
    "Distro:": "系统：",
    "Download + apply": "下载并应用",
    "Draw a spectrum from the microphone": "显示麦克风频谱",
    "Duration:": "时长：",
    "Edit the device's overlay layout.  The rows below are exactly what's on screen — editing one moves/changes it in place.": "编辑设备叠加层。下方条目就是屏幕上的元素，可直接调整位置和内容。",
    "Edit…": "编辑…",
    "Effect": "效果",
    "Enable zone-sync carousel": "启用分区同步轮播",
    "Enter an LED device key (e.g. 0416:8001) and pick a tab.": "输入 LED 设备键（例如 0416:8001），然后选择选项卡。",
    "Export": "导出",
    "Exporting…": "正在导出…",
    "Failed to write cropped image to a temporary file.": "裁剪图片无法写入临时文件。",
    "Fit height": "适应高度",
    "Fit mode:": "适应方式：",
    "Fit width": "适应宽度",
    "Font family; leave empty to keep the theme's own typeface.": "字体名称；留空则使用主题原有字体。",
    "Font:": "字体：",
    "Fast": "快",
    "Find lights": "查找灯光设备",
    "Follow": "联动",
    "Format string:": "格式字符串：",
    "Frame rate:": "帧率：",
    "Freeze the desktop and click a pixel to use its colour.": "冻结桌面并点击一个像素选取颜色。",
    "From screen…": "从屏幕取色…",
    "GPU:": "显卡：",
    "Game mode": "游戏模式",
    "Health": "健康检查",
    "Horizontal": "水平",
    "Hue scrolls smoothly through the spectrum on every tick.": "色相沿光谱平滑循环变化。",
    "Height (px):": "高度（像素）：",
    "Hide the frame around the region": "隐藏区域边框",
    "Image crop cancelled.": "已取消图片裁剪。",
    "Image crop produced no output — try a different file.": "图片裁剪未产生输出，请尝试其他文件。",
    "Include HDD metrics in broadcasts": "在数据广播中包含机械硬盘指标",
    "Inspector": "检查器",
    "Install:": "安装方式：",
    "Interval:": "间隔：",
    "LED animation mode": "LED 动画模式",
    "Layer:": "图层：",
    "Left": "向左",
    "Lights your memory, your motherboard's RGB and OpenRGB's devices -- with effects, or following a cooler or an LCD.": "控制内存、主板和 OpenRGB 设备灯光，可播放效果或跟随水冷屏幕。",
    "Language:": "语言：",
    "Load": "载入",
    "Load a video first.": "请先载入视频。",
    "Load follows:": "负载联动来源：",
    "Load theme": "载入主题",
    "Mask visible": "显示蒙板",
    "Mask:": "蒙板：",
    "Masks are images that punch a window through the background.  Apply one to see only that shape on your device.": "蒙板可限定背景的可见形状。应用后，屏幕只显示该形状内的内容。",
    "Media player:": "媒体播放器：",
    "Memory + disk (segment devices)": "内存与硬盘（分段设备）",
    "Memory slots:": "内存插槽：",
    "Maintenance": "维护",
    "Mapping": "映射",
    "Medium": "中等",
    "Metric source": "指标来源",
    "Metric id:": "指标 ID：",
    "Metric overlay:": "指标叠加层：",
    "Mode": "模式",
    "Mode:": "模式：",
    "Module:": "模块：",
    "Module picture in a box": "画中画模块",
    "Motherboard": "主板",
    "No change.": "没有变化。",
    "No devices scanned yet.": "尚未扫描设备。",
    "No frame can be shown on Wayland: a window cannot place itself there.  Use \"Choose region…\" to set the region.": "Wayland 无法显示取景边框，请使用“选择区域…”设置区域。",
    "No masks found.  Click 'Upload new mask…' to add a PNG / JPG image and apply it to your device.": "没有找到蒙板。点击“上传新蒙板…”添加 PNG/JPG 图片。",
    "Not casting.  Start mirrors the region shown.": "尚未投屏。点击“开始”镜像所选区域。",
    "Orientation:": "方向：",
    "Overlays audio bars on the cast frame.  Needs ``sounddevice``; without it the cast runs without bars.": "在投屏画面上显示音频柱形图；需要 sounddevice。",
    "Overrides the current mode + colour.  Useful for confirming the device responds at all.": "覆盖当前模式和颜色，用于确认设备是否响应。",
    "Overlay editor": "叠加层编辑器",
    "Panel / row": "面板／行",
    "Pick a device on the left to see its output.": "在左侧选择设备以查看输出。",
    "Pick a device to see and change its settings.": "选择设备以查看和修改设置。",
    "Paths:": "路径：",
    "Pause": "暂停",
    "Pick a category and refresh to load the catalog.": "请选择分类并刷新目录。",
    "Pick a device + a region, then Start to mirror the region to the device.": "选择设备和区域，再点击“开始”投屏。",
    "Pick a device first to list masks at its resolution.": "请先选择设备，以显示适配其分辨率的蒙板。",
    "Pick a device first to list themes at its resolution.": "请先选择设备，以显示适配其分辨率的主题。",
    "Pick a device first.  Open the Devices panel to scan if no devices are listed.": "请先选择设备；如果列表为空，请到“设备”页扫描。",
    "Pick a device first.  Open the Devices panel to scan.": "请先选择设备，再到“设备”页扫描。",
    "Pick a device first.  Use the Devices panel to scan if no devices are listed.": "请先选择设备；如果列表为空，请到“设备”页扫描。",
    "Pick a mask from the list first.": "请先从列表选择蒙板。",
    "Pick a row, not a panel heading.": "请选择数据行，不要选择面板标题。",
    "Pick a sensor": "选择传感器",
    "Pick a sensor first.": "请先选择传感器。",
    "Pick a sensor to see its current value.": "选择传感器以查看当前数值。",
    "Pick a theme from the list first.": "请先从列表选择主题。",
    "Pick a video, trim it, encode it as a Theme.zt animation, save it as a theme and apply it.": "选择视频并裁剪，将其编码为 Theme.zt 动画，保存为主题后应用。",
    "Pick an LED device to load its state.  Open the Devices panel to scan if no devices are listed.": "请选择 LED 设备；如果列表为空，请到“设备”页扫描。",
    "Pick an element from the list first.": "请先从列表选择元素。",
    "Pick an image, crop it to your device's resolution, save it as a theme and apply it.": "选择图片并裁剪至设备分辨率，保存为主题后应用。",
    "Pick color…": "选择颜色…",
    "Pick…": "选择…",
    "Play": "播放",
    "Play video…": "播放视频…",
    "Position + visibility": "位置与可见性",
    "Position:": "位置：",
    "Platform": "平台",
    "Presets": "预设",
    "Preview": "预览",
    "RGB:": "RGB：",
    "RGB Lighting": "RGB 灯效",
    "RAM lighting is not available on this system yet": "此系统暂不支持内存灯效",
    "RAM lighting is off": "内存灯效已关闭",
    "Re-run health check": "重新运行健康检查",
    "Recent events": "最近事件",
    "Refresh": "刷新",
    "Refresh interval:": "刷新间隔：",
    "Refresh playback position": "刷新播放位置",
    "Region selection cancelled.": "已取消区域选择。",
    "Region:": "区域：",
    "Right": "向右",
    "Regular": "普通",
    "Rename row…": "重命名行…",
    "Render size:": "渲染尺寸：",
    "Rescan for attached devices.": "重新扫描已连接设备。",
    "Reset": "重置",
    "Restore last theme": "恢复上次主题",
    "Roman": "罗马体",
    "Rotate through:": "轮播内容：",
    "Rotation interval:": "轮播间隔：",
    "Running checks…": "正在检查…",
    "Save bug report…": "保存故障报告…",
    "Save cancelled — choose a different name": "已取消保存，请换一个名称。",
    "Save current as…": "将当前内容另存为…",
    "Save layout": "保存布局",
    "Save slideshow": "保存幻灯片",
    "SDK server": "SDK 服务",
    "Same on every light": "所有灯光相同",
    "Sensors (live)": "实时传感器",
    "Six-phase gradient cycle running across each segment.": "六阶段渐变在各分区循环。",
    "Slow": "慢",
    "Smooth": "平滑",
    "Solid colour, no animation.": "纯色常亮，无动画。",
    "Speed": "速度",
    "Split left to right": "从左到右分屏",
    "Save the device's current rendered state (background, mask, overlay edits) as a new theme.": "将设备当前画面（背景、蒙板、叠加层）保存为新主题。",
    "Scan": "扫描",
    "Search by name, label, or category (e.g. 'cpu temp')…": "按名称、标签或分类搜索（例如“CPU 温度”）…",
    "Select a device first.": "请先选择设备。",
    "Select a device to inspect.": "选择设备以查看详情。",
    "Select a panel to delete.": "请选择要删除的面板。",
    "Select a panel to rename.": "请选择要重命名的面板。",
    "Select a theme first.": "请先选择主题。",
    "Sensor": "传感器",
    "Sensor linkage": "传感器联动",
    "Set background…": "设置背景…",
    "Set the background mode to 'Transparent' on the Configuration page before starting; otherwise the theme's background composites under the screencast.": "开始前请在“设置”页将背景模式设为“透明”，否则主题背景会出现在投屏下方。",
    "Show unit (e.g. °C, %, RPM)": "显示单位（例如 °C、%、RPM）",
    "Showing:": "显示：",
    "Size (px):": "尺寸（像素）：",
    "Slant:": "倾斜：",
    "Slideshow": "幻灯片",
    "Split mode:": "分屏模式：",
    "Start TRCC on login": "登录时启动 TRCC",
    "Start screencast": "开始投屏",
    "Start:": "开始：",
    "State": "状态",
    "State:": "状态：",
    "Status": "状态",
    "System": "系统",
    "Stop": "停止",
    "Takes the panel above CPU:": "屏幕优先于 CPU 的阈值：",
    "Target: (load a video)": "目标：（载入视频）",
    "Target: (load an image)": "目标：（载入图片）",
    "Temperature follows:": "温度联动来源：",
    "Temperature unit:": "温度单位：",
    "TRCC Linux — Thermalright LCD/LED Cooler Control": "TRCC Live2D — 利民水冷控制中心",
    "TRCC needs permission to reach the memory's lighting chips.  Nothing is changed until you turn it on, and you can turn it off here again.": "TRCC 需要权限访问内存灯控芯片。启用前不会修改灯光，也可随时关闭。",
    "Tick a header and give it the number of LEDs on its fan or strip.  A board listed as found has its own software; TRCC leaves it alone.": "勾选接口并填写风扇或灯条的 LED 数量。已识别的主板由其原有软件控制。",
    "Text:": "文字：",
    "That is the last panel — an empty layout is refused.": "这是最后一个面板，不能删除成空布局。",
    "The layout was saved in another window — Save layout keeps yours": "布局已在另一个窗口保存；点击“保存布局”可保留当前修改。",
    "Theme:": "主题：",
    "Themes:": "主题：",
    "Thermalright LCD/LED cooler control": "利民 LCD/LED 水冷控制",
    "This device has no separately-addressable zones.": "此设备没有可单独控制的分区。",
    "Time format:": "时间格式：",
    "Tips": "提示",
    "Type:": "类型：",
    "Up": "向上",
    "Unpack a .tr theme archive into your library.": "将 .tr 主题包解压到主题库。",
    "Upgrade now…": "立即升级…",
    "Upload new mask…": "上传新蒙板…",
    "Video crop cancelled.": "已取消视频裁剪。",
    "Video crop produced no output.": "视频裁剪未产生输出。",
    "Vertical": "垂直",
    "Vivid": "鲜艳",
    "Weight:": "字重：",
    "Width (px):": "宽度（像素）：",
    "X position:": "X 坐标：",
    "X:": "X：",
    "Y position:": "Y 坐标：",
    "Y:": "Y：",
    "Zip the selected theme to a shareable .tr archive.": "将选中的主题打包为可分享的 .tr 文件。",
    "Zones": "分区",
    "Zoom:": "缩放：",
    "e.g. cpu:temp": "例如 cpu:temp",
    "no video": "无视频",
}

# The Live2D panel currently has Chinese source strings. Keep it usable when
# the user switches back to English in TRCC's Configuration page.
LIVE2D_EN: dict[str, str] = {
    "Live2D 叠加层": "Live2D Overlay",
    "角色实时显示在水冷屏幕中，可由 CPU 温度驱动动作。": "The character appears on the cooler screen and reacts to CPU temperature.",
    "模型文件 (.model3.json)": "Model file (.model3.json)",
    "Cubism Core (live2dcubismcore.min.js)": "Cubism Core (live2dcubismcore.min.js)",
    "传感器键": "Sensor key",
    "升温阈值 °C": "Warm threshold °C",
    "高温阈值 °C": "Hot threshold °C",
    "在叠加层启用": "Enable in overlay",
    "请先连接并选择水冷屏幕，再启用叠加层。": "Connect and select a cooler screen, then enable the overlay.",
    "选择本机文件": "Choose a local file",
    "浏览…": "Browse…",
    "选择文件": "Choose file",
    "请先在设备页面连接并选中水冷屏幕。": "Connect and select the cooler screen on the Devices page.",
    "模型或 Cubism Core 文件不存在。": "The model or Cubism Core file does not exist.",
    "当前叠加层已有其他模块，请先在叠加编辑器中移除它。": "Remove the existing module in the overlay editor first.",
    "Live2D 已加入主题叠加层。": "Live2D has been added to the theme overlay.",
}

REVERSE_ZH = {value: key for key, value in
              {**TRANSLATIONS["zh"], **EXTRA_ZH}.items()}


def translate_text(text: str, language: str) -> str:
    if language == "en":
        return LIVE2D_EN.get(text, REVERSE_ZH.get(text, text))
    if language != "zh":
        return text
    if text in LIVE2D_EN:
        return text
    if text in EXTRA_ZH:
        return EXTRA_ZH[text]
    translated = TRANSLATIONS["zh"].get(text)
    if translated:
        return translated
    if text.endswith(":"):
        base = text[:-1]
        translated = EXTRA_ZH.get(base) or TRANSLATIONS["zh"].get(base)
        if translated:
            return translated + "："
    checks = re.fullmatch(r"(\d+) fail / (\d+) warn / (\d+) checks", text)
    if checks:
        return f"{checks[1]} 项失败 / {checks[2]} 项警告 / 共 {checks[3]} 项检查"
    themes = re.fullmatch(r"(\d+) cloud theme\(s\) in '([^']+)'", text)
    if themes:
        return f"分类“{themes[2]}”中有 {themes[1]} 个云端主题"
    if text.startswith("version "):
        return "版本 " + text[len("version "):]
    prefixes = {
        "Connected: ": "已连接：",
        "Disconnected: ": "已断开：",
        "Frame sent: ": "已发送帧：",
        "Debug report saved to ": "故障报告已保存到 ",
        "Error [": "错误 [",
    }
    for prefix, replacement in prefixes.items():
        if text.startswith(prefix):
            return replacement + text[len(prefix):]
    return text


class ChineseQtGui(QObject):
    """Translate widget text without touching device values or user input."""

    def __init__(self, qapp: QApplication, settings_file: Path) -> None:
        super().__init__(qapp)
        self.qapp = qapp
        self.settings_file = settings_file
        self.language = "zh"
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.refresh)

    def start(self) -> None:
        self.refresh()
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()

    def _read_language(self) -> str:
        try:
            data = json.loads(self.settings_file.read_text(encoding="utf-8"))
            return str(data.get("app", {}).get("language", "zh"))
        except (OSError, ValueError, TypeError):
            return "zh"

    def _apply(self, obj: QObject, getter: str, setter: str, prop: str) -> None:
        current = str(getattr(obj, getter)())
        original = obj.property(prop + "Original")
        previous = obj.property(prop + "Applied")
        if original is None or current != previous:
            original = current
        wanted = translate_text(str(original), self.language)
        if wanted != current:
            getattr(obj, setter)(wanted)
        obj.setProperty(prop + "Original", original)
        obj.setProperty(prop + "Applied", wanted)

    def _items(self, widget: QComboBox | QTabWidget, count: int,
               getter: str, setter: str, prop: str) -> None:
        cache = widget.property(prop) or {}
        updated = {}
        for index in range(count):
            current = str(getattr(widget, getter)(index))
            original, previous = cache.get(index, (current, None))
            if current != previous:
                original = current
            wanted = translate_text(original, self.language)
            if wanted != current:
                getattr(widget, setter)(index, wanted)
            updated[index] = (original, wanted)
        widget.setProperty(prop, updated)

    def refresh(self) -> None:
        self.language = self._read_language()
        for widget in self.qapp.allWidgets():
            if isinstance(widget, QAbstractButton):
                if widget.property("live2dModuleSwitch"):
                    on = widget.isChecked()
                    widget.setText(("已启用" if on else "已停用") if self.language == "zh" else ("Enabled" if on else "Disabled"))
                    widget.setToolTip(("点击停用此模块" if on else "点击启用此模块") if self.language == "zh" else ("Click to disable" if on else "Click to enable"))
                else:
                    self._apply(widget, "text", "setText", "zhText")
            elif isinstance(widget, QLabel):
                self._apply(widget, "text", "setText", "zhText")
            if isinstance(widget, QGroupBox):
                self._apply(widget, "title", "setTitle", "zhTitle")
            if isinstance(widget, QMainWindow):
                self._apply(widget, "windowTitle", "setWindowTitle", "zhWindowTitle")
            if isinstance(widget, QLineEdit):
                self._apply(widget, "placeholderText", "setPlaceholderText", "zhPlaceholder")
            if isinstance(widget, QComboBox):
                self._items(widget, widget.count(), "itemText", "setItemText", "zhComboItems")
            if isinstance(widget, QTabWidget):
                self._items(widget, widget.count(), "tabText", "setTabText", "zhTabItems")
            if isinstance(widget, QTableWidget):
                for index in range(widget.columnCount()):
                    item = widget.horizontalHeaderItem(index)
                    if item is not None:
                        item.setText(translate_text(item.text(), self.language))
            if isinstance(widget, QTreeWidget):
                item = widget.headerItem()
                if item is not None:
                    for index in range(widget.columnCount()):
                        item.setText(index, translate_text(item.text(index), self.language))
            actions = getattr(widget, "actions", None)
            for action in actions() if callable(actions) else ():
                if isinstance(action, QAction):
                    self._apply(action, "text", "setText", "zhAction")
            if isinstance(widget, QMenu):
                self._apply(widget, "title", "setTitle", "zhMenuTitle")


def launch_chinese() -> None:
    """Run the standard Qt GUI with a localized view layer."""
    from trcc.ui._uis import _QtUI
    from trcc.ui.cli.main import qtgui

    original_exec = _QtUI._exec

    def localized_exec(ui: _QtUI) -> int:
        qapp = QApplication.instance()
        assert isinstance(qapp, QApplication)
        root = Path(os.environ.get("APPDATA", str(Path.home())))
        translator = ChineseQtGui(qapp, root / "trcc" / "trcc.json")
        translator.start()
        try:
            return original_exec(ui)
        finally:
            translator.stop()

    _QtUI._exec = localized_exec
    qtgui(False)
