"""TRCC module root: a live character drawn by the existing panel pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from trcc.adapters.modules import BaseModule
from trcc.core.ports import BackgroundKind, ModuleHost
from trcc.core.results import Result

from .services.source import Live2DSource


class Live2DKind(BackgroundKind):
    prefix = "live2d"

    def __init__(self, module: "Live2DModule") -> None:
        self.module = module

    def play(self, key: str, payload: Mapping[str, Any]) -> Result:
        try:
            model = Path(str(payload.get("model", ""))).expanduser().resolve(strict=True)
            if model.suffix.lower() != ".json" or not model.name.endswith(".model3.json"):
                return Result(ok=False, message="请选择 Cubism 3/4 的 .model3.json 文件")
            core = Path(str(payload.get("core", ""))).expanduser().resolve(strict=True)
            size = self.module.host.panels.size(key)
            if size is None:
                return Result(ok=False, message="设备尚未连接")
            previous = self.module.active.get(key, {})
            running = self.module.host.background.source(key)
            if isinstance(running, Live2DSource) and previous.get("model") == payload.get("model") and previous.get("core") == payload.get("core") and all(previous.get("options", {}).get(k) == payload.get("options", {}).get(k) for k in ("resolution", "engine", "backend")):
                running.options = dict(payload.get("options", {}))
                running.sensor = str(payload.get("sensor", "cpu:temp"))
                running.warm = float(payload.get("warm", 55))
                running.hot = float(payload.get("hot", 75))
                self.module.active[key] = dict(payload)
                return Result(message="Live2D 参数已实时更新")
            requested = int(payload.get("options", {}).get("resolution", 2048))
            render_side = max(480, min(3072, requested or max(size)))
            source = Live2DSource(model, core, (render_side, render_side), self.module.host.readings,
                                  sensor=str(payload.get("sensor", "cpu:temp")),
                                  warm=float(payload.get("warm", 55)),
                                  hot=float(payload.get("hot", 75)),
                                  options=dict(payload.get("options", {})))
            self.module.host.background.show(key, source, fps=30)
            self.module.active[key] = dict(payload)
            return Result(message="Live2D 已启动")
        except (OSError, ValueError) as error:
            return Result(ok=False, message=str(error))

    def resume(self, key: str) -> None:
        payload = self.module.host.settings.panel(key)
        if payload.get("model"):
            self.play(key, payload)

    def snapshot(self, key: str) -> dict[str, Any] | None:
        return self.module.active.get(key)


class Live2DModule(BaseModule, key="live2d"):
    title = "Live2D"
    summary = "在水冷屏幕上实时播放随温度变化的角色。"
    default_on = False

    def __init__(self) -> None:
        self.active: dict[str, dict[str, Any]] = {}

    def _enable(self, host: ModuleHost) -> None:
        self.host = host
        # The shared App may be the frozen base installation. Apply the
        # geometry correction there too, not only in the embedded Python copy.
        from trcc.core import geometry
        from trcc.services import display
        def unclipped_rect(canvas, x, y, width, height):
            if width <= 0 or height <= 0:
                return None
            return geometry.FitRect(width, height, x, y)
        geometry.element_rect = unclipped_rect
        display.element_rect = unclipped_rect
        # Install in the shared App as well as the embedded Python build.
        from trcc.services.layers import Mask, Overlay
        service = display.DisplayService
        if not getattr(service, "_live2d_mask_toggle", False):
            original_layers = service._layers_over_background
            original_mask = service._mask_layer
            def enabled(settings):
                return settings.module_settings.get("live2d", {}).get("options", {}).get("maskAbove", True)
            def mask_layer(instance, info, settings, theme):
                layer = original_mask(instance, info, settings, theme)
                if enabled(settings):
                    instance.__dict__.setdefault("_live2d_front_masks", {})[info.key] = layer
                    return Mask(None)
                return layer
            def layers(instance, info, settings, *args, **kwargs):
                result = list(original_layers(instance, info, settings, *args, **kwargs))
                mask = instance.__dict__.get("_live2d_front_masks", {}).get(info.key)
                if enabled(settings) and mask is not None and settings.mask_visible:
                    # Metrics are rendered as a single surface. Put mask immediately
                    # before that surface, above the live module picture.
                    at = next((i for i, layer in enumerate(result) if isinstance(layer, Overlay)), len(result))
                    result.insert(at, mask)
                return result
            service._mask_layer = mask_layer
            service._layers_over_background = layers
            service._live2d_mask_toggle = True
        self.kind = Live2DKind(self)
        host.themes.add_kind(self.kind)

    def _disable(self, host: ModuleHost) -> None:
        self.active.clear()

    def configure(self, key: str, payload: dict[str, Any]) -> Result:
        if not payload["sensor"].strip():
            return Result(ok=False, message="请输入传感器键，例如 cpu:temp")
        if payload["warm"] >= payload["hot"]:
            return Result(ok=False, message="高温阈值必须大于升温阈值")
        if not Path(payload["model"]).is_file() or not Path(payload["core"]).is_file():
            return Result(ok=False, message="模型或 Cubism Core 文件不存在")
        self.host.settings.save_panel(key, payload)
        return Result(message="Live2D 配置已保存")

    def activate(self, key: str) -> Result:
        payload = self.host.settings.panel(key)
        if not payload.get("model"):
            return Result(ok=False, message="请先选择 Live2D 模型")
        return self.kind.play(key, payload)
