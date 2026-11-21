"""Latest-frame adapter from headless Cubism renderer to TRCC RawFrame."""
from __future__ import annotations

import json
import os
import sys
import struct
import subprocess
import threading
from pathlib import Path

from PySide6.QtGui import QImage

from trcc.core.models import RawFrame
from trcc.core.ports import CaptureNotReady, FrameSource, ReadingsPort


class Live2DSource(FrameSource):
    name = "Live2D"

    def __init__(self, model: Path, core: Path, size: tuple[int, int],
                 readings: ReadingsPort, *, sensor: str, warm: float, hot: float, options: dict | None = None) -> None:
        self.options = options or {}
        self.readings = readings
        self.sensor = sensor
        self.warm = warm
        self.hot = hot
        self._frame: RawFrame | None = None
        self._error: str | None = None
        self._lock = threading.Lock()
        self._closed = False
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "TRCCLive2D" / "renderer"
        if not (root / "server.mjs").is_file():
            root = Path(os.environ.get("TRCC_LIVE2D_HOME", str(Path.home()))) / "renderer"
        script = root / "server.mjs"
        if not (root / "dist" / "renderer.html").is_file():
            raise OSError("未构建渲染器：请在 live2d/renderer 运行 npm run build")
        self._native = self.options.get("engine") == "native"
        command = ["node", str(script), str(model), str(core), str(size[0]), str(size[1]), str(self.options.get("engine", "classic")), str(self.options.get("backend", "software"))]
        if self._native:
            python = root.parents[2] / "python" / "python.exe"
            if not python.is_file():
                python = Path(os.environ.get("TRCC_LIVE2D_PYTHON", sys.executable))
            command = [str(python), str(root / "native_renderer.py"), str(model), str(size[0]), str(size[1])]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=os.environ.copy(),
            bufsize=0, creationflags=creationflags,
        )
        threading.Thread(target=self._read_frames, name="live2d-frames", daemon=True).start()
        threading.Thread(target=self._read_errors, name="live2d-errors", daemon=True).start()

    def _read_exact(self, count: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < count:
            part = self._process.stdout.read(count - len(chunks))
            if not part:
                raise EOFError("Live2D 渲染进程已退出")
            chunks.extend(part)
        return bytes(chunks)

    def _read_frames(self) -> None:
        try:
            while not self._closed:
                length = struct.unpack("<I", self._read_exact(4))[0]
                if length < 8 or length > 64_000_000:
                    raise ValueError("渲染器返回了无效帧")
                if self._native:
                    width, height = struct.unpack("<II", self._read_exact(8))
                    if width < 1 or height < 1 or length != width * height * 4:
                        raise ValueError("无效的原生 RGBA 帧")
                    data = self._read_exact(length)
                    with self._lock:
                        self._frame = RawFrame(data, width, height)
                    continue
                png = self._read_exact(length)
                image = QImage.fromData(png, "PNG")
                if image.isNull():
                    raise ValueError("无法解码 Live2D 帧")
                image = image.convertToFormat(QImage.Format.Format_RGBA8888)
                data = image.bits().tobytes()
                with self._lock:
                    self._frame = RawFrame(data, image.width(), image.height())
        except (EOFError, ValueError, OSError) as error:
            if not self._closed:
                self._error = str(error)

    def _read_errors(self) -> None:
        # Drain stderr so a verbose Chromium process cannot block stdout.
        for line in self._process.stderr:
            if line.startswith(b"FATAL:"):
                self._error = line.decode("utf-8", "replace").strip()

    def latest(self) -> RawFrame:
        if self._error:
            raise OSError(self._error)
        readings = self.readings.latest() or {}
        value = readings.get(self.sensor)
        if self._process.stdin and self._process.poll() is None:
            try:
                message = json.dumps({"temperature": value, "warm": self.warm,
                                      "hot": self.hot, "options": self.options}) + "\n"
                self._process.stdin.write(message.encode())
            except (BrokenPipeError, OSError):
                pass
        with self._lock:
            if self._frame is None:
                raise CaptureNotReady("Live2D 渲染器正在启动")
            return self._frame

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
