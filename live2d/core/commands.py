"""Configure a live character through TRCC's command bus."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from trcc.core.commands._base import ModuleCommand
from trcc.core.results import Result


@dataclass(frozen=True, slots=True)
class SetLive2D(ModuleCommand[Result, "Live2DModule"]):
    MODULE: ClassVar[str] = "live2d"
    key: str
    model: str
    core: str
    sensor: str = "cpu:temp"
    warm: float = 55
    hot: float = 75
    options: dict | None = None

    def run(self, module: "Live2DModule") -> Result:
        return module.configure(self.key, {
            "model": self.model, "core": self.core, "sensor": self.sensor,
            "warm": self.warm, "hot": self.hot, "options": self.options or {},
        })


@dataclass(frozen=True, slots=True)
class StartLive2D(ModuleCommand[Result, "Live2DModule"]):
    MODULE: ClassVar[str] = "live2d"
    key: str

    def run(self, module: "Live2DModule") -> Result:
        return module.activate(self.key)
