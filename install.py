"""Install the Live2D extension into an existing TRCC Linux Windows install."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MODULE = ROOT / "live2d"
RENDERER = ROOT / "renderer"
TARGET = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "TRCCLive2D" / "renderer"


def run(*args: str, cwd: Path | None = None) -> None:
    print("运行:", " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def main() -> None:
    if not (MODULE / "module.json").is_file():
        raise SystemExit("项目缺少 live2d/module.json")
    try:
        import trcc  # noqa: F401
    except ImportError as error:
        raise SystemExit("请先运行：py -3.12 -m pip install trcc-linux==9.12.2") from error
    run(sys.executable, "-m", "pip", "install", "live2d-py==1.0.0", "PyOpenGL==3.1.10")
    shutil.copytree(RENDERER, TARGET, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("node_modules", "dist"))
    npm = shutil.which("npm")
    npx = shutil.which("npx")
    if not npm or not npx:
        raise SystemExit("未找到 Node.js 的 npm/npx，请先安装 Node.js 20+")
    run(npm, "install", "--no-audit", "--no-fund", cwd=TARGET)
    run(npm, "run", "build", cwd=TARGET)
    run(npx, "playwright", "install", "chromium", cwd=TARGET)
    run(sys.executable, "-m", "trcc", "system", "modules", "developer", "on")
    run(sys.executable, "-m", "trcc", "system", "modules", "install-folder", str(MODULE), "--yes")
    run(sys.executable, "-m", "trcc", "config", "language", "zh")
    print("安装完成。运行 run.ps1，在模块页打开 Live2D。")
    print("请在 Live2D 页面选择模型和官方 Cubism Core 文件。")


if __name__ == "__main__":
    main()
