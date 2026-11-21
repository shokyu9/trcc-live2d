"""Launch TRCC's Qt GUI with Chinese language support."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from localization.qt_zh import launch_chinese


if __name__ == "__main__":
    launch_chinese()
