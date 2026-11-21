"""Fluent-inspired Live2D setup page inside TRCC's Qt GUI."""
import os
import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QDoubleSpinBox, QComboBox, QCheckBox, QTextEdit)

from trcc.core.commands.device import DeviceCanvas, EnableOverlay, PlaceModule, ResolveOverlay, UpdateOverlayElement
from trcc.ui.qtgui.base import BasePanel
from ...core.commands import SetLive2D, StartLive2D


class Live2DPanel(BasePanel):
    LABEL = "Live2D"

    def _setup_ui(self) -> None:
        self.setObjectName("Live2DPanel")
        self.setStyleSheet("""
          #Live2DPanel { background: #f7f9fc; color: #20242b; }
          QLabel { color: #303641; font-size: 13px; }
          QLineEdit, QSpinBox { background: white; border: 1px solid #d5dce5;
            border-radius: 7px; min-height: 34px; padding: 3px 8px; color: #20242b; }
          QPushButton { background: white; border: 1px solid #d1d8e2;
            border-radius: 7px; min-height: 34px; padding: 3px 13px; color: #20242b; }
          QPushButton:hover { background: #eef5ff; }
          QPushButton#Primary { background: #0067c0; color: white; border: 0; }
          QPushButton#Primary:hover { background: #197bd0; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 26, 28, 26)
        root.setSpacing(13)
        title = QLabel("Live2D 叠加层")
        title.setStyleSheet("font-size: 25px; font-weight: 650; color: #1b1e24")
        root.addWidget(title)
        root.addWidget(QLabel("角色实时显示在水冷屏幕中，可由 CPU 温度驱动动作。"))
        self.model = self._file_row(root, "模型文件 (.model3.json)", "Live2D 模型 (*.model3.json)")
        self.core = self._file_row(root, "Cubism Core (live2dcubismcore.min.js)", "JavaScript (*.js)")
        install_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))).parent
        if not (install_root / "models").is_dir():
            install_root = Path(os.environ.get("TRCC_LIVE2D_HOME", str(Path.home())))
        models = sorted((install_root / "models").rglob("*.model3.json"))
        if models:
            self.model.setText(str(models[0]))
        core_file = install_root / "data" / "TRCCLive2D" / "renderer" / "live2dcubismcore.min.js"
        if core_file.is_file():
            self.core.setText(str(core_file))
        root.addWidget(QLabel("传感器键"))
        self.sensor = QLineEdit("cpu:temp")
        root.addWidget(self.sensor)
        thresholds = QHBoxLayout()
        for label, value, attr in [("升温阈值 °C",55,"warm"),("高温阈值 °C",75,"hot")]:
            column = QVBoxLayout(); column.addWidget(QLabel(label))
            box = QSpinBox(); box.setRange(0,120); box.setValue(value)
            setattr(self, attr, box); column.addWidget(box); thresholds.addLayout(column)
        root.addLayout(thresholds)
        self.scale = QDoubleSpinBox(); self.scale.setRange(.1, 8); self.scale.setSingleStep(.1); self.scale.setValue(1)
        root.addWidget(QLabel("模型缩放（整个图层缩放，仅屏幕边缘裁剪）")); root.addWidget(self.scale)
        root.addWidget(QLabel("渲染分辨率（提高后更清晰，也会增加资源占用）"))
        self.engine = QComboBox(); self.engine.addItem("Classic / PixiJS 6", "classic"); self.engine.addItem("LipsyncPatch / PixiJS 7（实验）", "lipsync")
        self.engine.addItem("Cubism Native SDK / OpenGL（live2d-py）", "native")
        root.addWidget(QLabel("Live2D 渲染适配器")); root.addWidget(self.engine)
        self.backend = QComboBox(); self.backend.addItem("软件 WebGL（兼容）", "software"); self.backend.addItem("硬件 WebGL（GPU）", "hardware")
        root.insertWidget(2, QLabel("GPU 硬件加速 / 渲染后端")); root.insertWidget(3, self.backend)
        self.fps = QSpinBox(); self.fps.setRange(4,30); self.fps.setValue(8)
        root.insertWidget(4, QLabel("渲染帧率（降低可减少占用）")); root.insertWidget(5, self.fps)
        self.resolution = QComboBox()
        for caption, pixels in [("自动（匹配图层）", 0), ("480 × 480",480), ("960 × 960",960), ("1440 × 1440",1440), ("2048 × 2048",2048), ("3072 × 3072",3072)]:
            self.resolution.addItem(caption, pixels)
        self.resolution.setCurrentIndex(4)
        root.addWidget(self.resolution)
        offsets = QHBoxLayout()
        self.offset_x = QSpinBox(); self.offset_y = QSpinBox()
        for caption, control in [("水平偏移（像素）", self.offset_x), ("垂直偏移（像素）", self.offset_y)]:
            control.setRange(-4096,4096); offsets.addWidget(QLabel(caption)); offsets.addWidget(control)
        root.addLayout(offsets)
        self.motion = QComboBox(); self.expression = QComboBox()
        self.motion.addItem("自动闲置", ""); self.expression.addItem("自动表情", "")
        root.addWidget(QLabel("动作 / 表情")); root.addWidget(self.motion); root.addWidget(self.expression)
        self.mask_above = QCheckBox("蒙版遮罩覆盖模型（温度文字保持在上方）")
        self.mask_above.setChecked(True); root.addWidget(self.mask_above)
        self.blink = QCheckBox("自动眨眼"); self.blink.setChecked(True)
        self.breath = QCheckBox("自动呼吸"); self.breath.setChecked(True)
        self.sway = QCheckBox("闲置转头与身体摆动"); self.sway.setChecked(True)
        idle_row = QHBoxLayout()
        for control in (self.blink,self.breath,self.sway): idle_row.addWidget(control)
        root.addLayout(idle_row)
        self.idle_strength = QDoubleSpinBox(); self.idle_strength.setRange(0,2); self.idle_strength.setSingleStep(.1); self.idle_strength.setValue(1)
        self.breath_speed = QDoubleSpinBox(); self.breath_speed.setRange(.25,3); self.breath_speed.setSingleStep(.1); self.breath_speed.setValue(1)
        idle_settings = QHBoxLayout(); idle_settings.addWidget(QLabel("摆动幅度")); idle_settings.addWidget(self.idle_strength); idle_settings.addWidget(QLabel("呼吸速度")); idle_settings.addWidget(self.breath_speed); root.addLayout(idle_settings)
        self.thermal = QCheckBox("启用温度联动"); self.thermal.setChecked(True); root.addWidget(self.thermal)
        root.addWidget(QLabel('高级参数 / 图层透明度（JSON，例如 {"parameters":{"ParamAngleX":15},"parts":{"PartArm":0.5}}）'))
        self.custom = QTextEdit(); self.custom.setPlainText('{}'); self.custom.setMaximumHeight(70); root.addWidget(self.custom)
        self.model.textChanged.connect(self._load_model_options)
        self._load_model_options()
        button = QPushButton("在叠加层启用")
        button.setObjectName("Primary")
        button.clicked.connect(self._activate)
        root.addWidget(button)
        self.status = QLabel("请先连接并选择水冷屏幕，再启用叠加层。")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        root.addStretch()
        self._preferences = QSettings("TRCCLive2D", "ModelControls")
        self._restore_controls()
        self._update_timer = QTimer(self); self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(250); self._update_timer.timeout.connect(self._apply_live)
        for control in (self.scale, self.offset_x, self.offset_y, self.warm, self.hot, self.fps):
            control.valueChanged.connect(self._schedule_update)
        for control in (self.model, self.core, self.sensor):
            control.textChanged.connect(self._schedule_update)
        self.custom.textChanged.connect(self._schedule_update)
        for control in (self.blink,self.breath,self.sway): control.toggled.connect(self._schedule_update)
        for control in (self.idle_strength,self.breath_speed): control.valueChanged.connect(self._schedule_update)
        self.mask_above.toggled.connect(self._schedule_update)
        self.thermal.toggled.connect(self._schedule_update)
        self.engine.currentIndexChanged.connect(self._schedule_update)
        self.backend.currentIndexChanged.connect(self._schedule_update)
        self.resolution.currentIndexChanged.connect(self._schedule_update)
        self.motion.currentIndexChanged.connect(self._schedule_update)
        self.expression.currentIndexChanged.connect(self._schedule_update)

    def _restore_controls(self):
        prefs = self._preferences
        for name in ("model", "core", "sensor"):
            value = prefs.value(name)
            if value is not None: getattr(self, name).setText(str(value))
        for name in ("scale", "offset_x", "offset_y", "warm", "hot", "fps"):
            value = prefs.value(name)
            if value is not None:
                getattr(self, name).setValue(float(value) if name == "scale" else int(float(value)))
        for name in ("engine", "backend"):
            control = getattr(self, name); index = control.findData(prefs.value(name, "classic" if name == "engine" else "software"))
            if index >= 0: control.setCurrentIndex(index)
        index = self.resolution.findData(int(prefs.value("resolution", 2048)))
        if index >= 0: self.resolution.setCurrentIndex(index)
        for name in ("blink","breath","sway"):
            getattr(self,name).setChecked(str(prefs.value(name,"true")).lower()=="true")
        for name in ("idle_strength","breath_speed"):
            getattr(self,name).setValue(float(prefs.value(name,1)))
        self.mask_above.setChecked(str(prefs.value("mask_above", "true")).lower()=="true")
        self.custom.setPlainText(str(prefs.value("custom", "{}")))
        self.thermal.setChecked(str(prefs.value("thermal", "true")).lower() == "true")
        for name in ("motion", "expression"):
            control = getattr(self, name); index = control.findData(prefs.value(name, ""))
            if index >= 0: control.setCurrentIndex(index)

    def _schedule_update(self, *_args):
        self._update_timer.start()

    def _apply_live(self):
        try:
            data = json.loads(self.custom.toPlainText())
            if not isinstance(data, dict): return
        except ValueError: return
        for name in ("model", "core", "sensor"):
            self._preferences.setValue(name, getattr(self, name).text())
        for name in ("scale", "offset_x", "offset_y", "warm", "hot", "fps"):
            self._preferences.setValue(name, getattr(self, name).value())
        for name in ("motion", "expression"):
            self._preferences.setValue(name, getattr(self, name).currentData())
        self._preferences.setValue("engine", self.engine.currentData())
        self._preferences.setValue("backend", self.backend.currentData())
        self._preferences.setValue("resolution", self.resolution.currentData())
        self._preferences.setValue("custom", self.custom.toPlainText())
        self._preferences.setValue("thermal", self.thermal.isChecked())
        for name in ("blink","breath","sway"): self._preferences.setValue(name,getattr(self,name).isChecked())
        for name in ("idle_strength","breath_speed"): self._preferences.setValue(name,getattr(self,name).value())
        self._preferences.setValue("mask_above",self.mask_above.isChecked())
        self._preferences.sync()
        if not self.device_key: return
        layout = self.dispatch(ResolveOverlay(key=self.device_key))
        if any(item.type == "module" and item.ref.startswith("live2d/") for item in layout.elements):
            self._activate()


    def _load_model_options(self, *_args) -> None:
        try:
            data = json.loads(Path(self.model.text()).read_text(encoding="utf-8"))
            refs = data.get("FileReferences", {})
            self.motion.clear(); self.motion.addItem("自动闲置", "")
            self.expression.clear(); self.expression.addItem("自动表情", "")
            for name in refs.get("Motions", {}): self.motion.addItem(name, name)
            for item in refs.get("Expressions", []): self.expression.addItem(item["Name"], item["Name"])
        except (OSError, ValueError, KeyError): pass

    def _file_row(self, root: QVBoxLayout, title: str, pattern: str) -> QLineEdit:
        root.addWidget(QLabel(title))
        row = QHBoxLayout()
        line = QLineEdit(); line.setPlaceholderText("选择本机文件")
        browse = QPushButton("浏览…")
        browse.clicked.connect(lambda: self._browse(line, pattern))
        row.addWidget(line, 1); row.addWidget(browse)
        root.addLayout(row)
        return line

    def _browse(self, line: QLineEdit, pattern: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", pattern)
        if path: line.setText(path)

    def _activate(self) -> None:
        key = self.device_key
        if not key:
            self.status.setText("请先在设备页面连接并选中水冷屏幕。")
            return
        model = Path(self.model.text())
        core = Path(self.core.text())
        if not model.is_file() or not core.is_file():
            self.status.setText("模型或 Cubism Core 文件不存在。")
            return
        try:
            options = json.loads(self.custom.toPlainText())
            if not isinstance(options, dict): raise ValueError("必须为 JSON 对象")
            for section in ("parameters", "parts"):
                if section in options and not isinstance(options[section], dict): raise ValueError(section + " 必须为对象")
            options.update(scale=1, x=0, y=0, resolution=self.resolution.currentData(), engine=self.engine.currentData(), backend=self.backend.currentData(), fps=self.fps.value(),
                           motion=self.motion.currentData(), expression=self.expression.currentData(), temperature=self.thermal.isChecked(), maskAbove=self.mask_above.isChecked(), autoBlink=self.blink.isChecked(), autoBreath=self.breath.isChecked(), autoSway=self.sway.isChecked(), idleStrength=self.idle_strength.value(), breathSpeed=self.breath_speed.value())
        except ValueError as error:
            self.status.setText("配置格式错误：" + str(error)); return
        result = self.dispatch(SetLive2D(
            key=key, model=str(model), core=str(core), sensor=self.sensor.text().strip(),
            warm=self.warm.value(), hot=self.hot.value(), options=options))
        if not result.ok:
            self.status.setText(result.message)
            return
        canvas = self.dispatch(DeviceCanvas(key=key))
        if not canvas.ok:
            self.status.setText(canvas.message)
            return
        layout = self.dispatch(ResolveOverlay(key=key))
        existing = next((item for item in layout.elements if item.type == "module"), None)
        if existing and not existing.ref.startswith("live2d/"):
            self.status.setText("当前叠加层已有其他模块，请先在叠加编辑器中移除它。")
            return
        layer_w = max(1, round(canvas.width * self.scale.value()))
        layer_h = max(1, round(canvas.height * self.scale.value()))
        layer_x = round((canvas.width - layer_w) / 2) + self.offset_x.value()
        layer_y = round((canvas.height - layer_h) / 2) + self.offset_y.value()
        if existing:
            changed = self.dispatch(UpdateOverlayElement(key=key, element_id=existing.id,
                x=layer_x, y=layer_y, width=layer_w, height=layer_h))
            if not changed.ok:
                self.status.setText(changed.message); return
        if not existing:
            placed = self.dispatch(PlaceModule(
                key=key, module="live2d", x=layer_x, y=layer_y, width=layer_w, height=layer_h))
            if not placed.ok:
                self.status.setText(placed.message)
                return
        started = self.dispatch(StartLive2D(key=key))
        if not started.ok:
            self.status.setText(started.message)
            return
        enabled = self.dispatch(EnableOverlay(key=key, enabled=True))
        self.status.setText("Live2D 已加入主题叠加层。" if enabled.ok else enabled.message)
