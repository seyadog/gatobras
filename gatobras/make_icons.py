"""Genera un .iconset (PNGs) desde assets/gatobras.svg. Uso: python -m gatobras.make_icons <carpeta.iconset>"""
import sys
from pathlib import Path

from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main(out):
    app = QGuiApplication([])  # noqa: F841
    svg = QSvgRenderer(str(Path(__file__).resolve().parent.parent / "assets" / "gatobras.svg"))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for base in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            px = base * scale
            img = QImage(px, px, QImage.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))
            p = QPainter(img)
            svg.render(p)
            p.end()
            img.save(str(out / f"icon_{base}x{base}{'@2x' if scale == 2 else ''}.png"))


if __name__ == "__main__":
    main(sys.argv[1])
