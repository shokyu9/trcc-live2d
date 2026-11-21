"""Remove the inspirations prose; keep all dependency license credits."""
from pathlib import Path
import trcc
path = Path(trcc.__file__).parent / "ui/qtgui/panels/about_panel.py"
text = path.read_text(encoding="utf-8")
marker = "        from ....core.credits import GROUPS, INSPIRATIONS"
if marker in text:
    start = text.index(marker)
    end = text.index("        for title, credits in GROUPS:", start)
    backup = path.with_suffix(".py.before-customization")
    if not backup.exists(): backup.write_text(text, encoding="utf-8")
    text = text[:start] + "        from ....core.credits import GROUPS\n        parts = []\n" + text[end:]
    path.write_text(text, encoding="utf-8")
print("About page customized; dependency credits preserved")
