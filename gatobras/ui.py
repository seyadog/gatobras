"""Interfaz Qt de gatobras."""
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRectF, QRunnable, QSize, Qt, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QImage, QImageReader, QPainter, QPen, QPixmap, QTransform
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QGridLayout, QGroupBox,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSplitter,
                               QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import core
from .core import GatoError

TIPOS = ["", "óleo", "acuarela", "acrílico", "dibujo", "grabado", "fotografía", "escultura", "objeto"]
LIST_THUMB, TABLE_THUMB, PREVIEW_SIDE = 96, 150, 1800

STYLE = """
* { font-size: 14px; }
QMainWindow, QWidget { background: #242424; color: #ffffff; }
QLabel { background: transparent; }
QTabWidget::pane { border: none; }
QGroupBox QGroupBox { background: #292929; }
QTabBar::tab { background: transparent; color: #9a9996; padding: 8px 18px; border-radius: 8px; margin: 4px 2px; }
QTabBar::tab:selected { background: #3d3d3d; color: #ffffff; }
QGroupBox { background: #303030; border: none; border-radius: 12px; margin-top: 22px; padding: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 6px; top: 0px; color: #9a9996; font-weight: bold; }
QLineEdit, QComboBox { background: #3d3d3d; border: 2px solid transparent; border-radius: 8px; padding: 6px 8px;
                       selection-background-color: #3584e4; }
QLineEdit:focus, QComboBox:focus { border-color: #3584e4; }
QComboBox QAbstractItemView { background: #3d3d3d; selection-background-color: #3584e4; }
QPushButton { background: #3d3d3d; border: none; border-radius: 8px; padding: 8px 14px; }
QPushButton:hover { background: #4a4a4a; }
QPushButton#primary { background: #3584e4; font-weight: bold; }
QPushButton#primary:hover { background: #4a95f0; }
QPushButton:pressed { background: #555555; }
QPushButton:disabled { color: #77767b; background: #333333; }
QListWidget { background: #1e1e1e; border: none; border-radius: 10px; padding: 6px; outline: none; }
QListWidget::item { border-radius: 8px; padding: 4px; color: #deddda; }
QListWidget::item:selected { background: #3584e4; color: #ffffff; }
QTableWidget { background: #1e1e1e; border: none; border-radius: 10px; gridline-color: #333333;
               selection-background-color: #3584e4; alternate-background-color: #242424; }
QHeaderView::section { background: #303030; color: #9a9996; border: none; padding: 6px; font-weight: bold; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #555555; border-radius: 5px; min-height: 30px; }
QScrollBar:horizontal { background: transparent; height: 10px; }
QScrollBar::handle:horizontal { background: #555555; border-radius: 5px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QSplitter::handle { background: transparent; }
QStatusBar { background: #1e1e1e; color: #9a9996; }
QToolTip { background: #3d3d3d; color: #ffffff; border: none; padding: 4px; }
QMessageBox, QDialog { background: #303030; }
"""


def load_scaled(path, side):
    """Lee la imagen reducida (decodificación escalada) con la orientación EXIF aplicada."""
    r = QImageReader(str(path))
    r.setAutoTransform(True)
    size = r.size()
    if size.isValid() and max(size.width(), size.height()) > side:
        r.setScaledSize(size.scaled(side, side, Qt.KeepAspectRatio))
    img = r.read()
    if not img.isNull() and max(img.width(), img.height()) > side:
        img = img.scaled(side, side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return img


class _Job(QRunnable):
    def __init__(self, loader, path, side):
        super().__init__()
        self.loader, self.path, self.side = loader, path, side

    def run(self):
        self.loader.ready.emit(self.path, self.side, load_scaled(self.path, self.side))


class Loader(QObject):
    """Carga miniaturas en segundo plano con caché."""
    ready = Signal(str, int, QImage)

    def __init__(self):
        super().__init__()
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(4)
        self.cache = {}
        self.pending = set()
        self.ready.connect(self._store)

    def _store(self, path, side, img):
        self.pending.discard((path, side))
        self.cache[(path, side)] = QPixmap.fromImage(img)

    def get(self, path, side):
        """Devuelve el pixmap si está en caché; si no, lo pide (llega por la señal `ready`)."""
        key = (str(path), side)
        if key in self.cache:
            return self.cache[key]
        if key not in self.pending:
            self.pending.add(key)
            self.pool.start(_Job(self, *key))
        return None


class Preview(QLabel):
    def __init__(self):
        super().__init__("Elige una carpeta de fotos (arriba a la izquierda)")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(300, 300)
        self.setStyleSheet("background:#1e1e1e; color:#9a9996; border-radius:12px")
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.img = None

    def set_image(self, img, text=""):
        self.img = img
        if img is None:
            self.setPixmap(QPixmap())
            self.setText(text)
        else:
            self._fit()

    def _fit(self):
        if self.img:
            self.setPixmap(QPixmap.fromImage(self.img).scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()


def apply_edit(img, rot, crop):
    """Aplica giro (múltiplo de 90°) y recorte (l, t, r, b normalizados sobre la imagen ya girada)."""
    if rot % 360:
        img = img.transformed(QTransform().rotate(rot % 360))
    if crop:
        w, h = img.width(), img.height()
        l, t, r, b = crop
        rect = (round(l * w), round(t * h), max(1, round((r - l) * w)), max(1, round((b - t) * h)))
        img = img.copy(*rect)
    return img


class CropView(QWidget):
    """Imagen con un rectángulo de recorte que se crea, mueve y redimensiona con el ratón."""
    MARGIN = 12

    def __init__(self):
        super().__init__()
        self.pm = None
        self.crop = None  # [l, t, r, b] normalizados
        self.mode = None
        self.setMinimumSize(520, 420)
        self.setMouseTracking(True)

    def set_image(self, img):
        self.pm = QPixmap.fromImage(img)
        self.update()

    def _disp(self):
        if not self.pm:
            return QRectF()
        box = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        sc = min(box.width() / self.pm.width(), box.height() / self.pm.height())
        w, h = self.pm.width() * sc, self.pm.height() * sc
        return QRectF(box.center().x() - w / 2, box.center().y() - h / 2, w, h)

    def _to_w(self, c):
        d = self._disp()
        return QRectF(d.left() + c[0] * d.width(), d.top() + c[1] * d.height(),
                      (c[2] - c[0]) * d.width(), (c[3] - c[1]) * d.height())

    def _to_n(self, p):
        d = self._disp()
        return (min(max((p.x() - d.left()) / d.width(), 0), 1), min(max((p.y() - d.top()) / d.height(), 0), 1))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor("#1e1e1e"))
        if not self.pm:
            return
        d = self._disp()
        p.drawPixmap(d, self.pm, QRectF(self.pm.rect()))
        if self.crop:
            r = self._to_w(self.crop)
            shade = QColor(0, 0, 0, 150)
            for a in (QRectF(d.left(), d.top(), d.width(), r.top() - d.top()),
                      QRectF(d.left(), r.bottom(), d.width(), d.bottom() - r.bottom()),
                      QRectF(d.left(), r.top(), r.left() - d.left(), r.height()),
                      QRectF(r.right(), r.top(), d.right() - r.right(), r.height())):
                p.fillRect(a, shade)
            p.setPen(QPen(QColor(255, 255, 255, 90), 1))
            for i in (1, 2):
                p.drawLine(QPointF(r.left() + r.width() * i / 3, r.top()), QPointF(r.left() + r.width() * i / 3, r.bottom()))
                p.drawLine(QPointF(r.left(), r.top() + r.height() * i / 3), QPointF(r.right(), r.top() + r.height() * i / 3))
            p.setPen(QPen(QColor("#3584e4"), 2))
            p.drawRect(r)
            p.setBrush(QColor("#ffffff"))
            for x in (r.left(), r.center().x(), r.right()):
                for y in (r.top(), r.center().y(), r.bottom()):
                    if (x, y) != (r.center().x(), r.center().y()):
                        p.drawRect(QRectF(x - 4, y - 4, 8, 8))

    def _hit(self, pos):
        r = self._to_w(self.crop)
        m = self.MARGIN
        near = lambda a, b: abs(a - b) <= m
        inx, iny = r.left() - m <= pos.x() <= r.right() + m, r.top() - m <= pos.y() <= r.bottom() + m
        edges = set()
        if iny and near(pos.x(), r.left()): edges.add("l")
        if iny and near(pos.x(), r.right()): edges.add("r")
        if inx and near(pos.y(), r.top()): edges.add("t")
        if inx and near(pos.y(), r.bottom()): edges.add("b")
        if edges:
            return ("resize", edges)
        if r.contains(pos):
            return ("move", None)
        return ("new", None)

    def mousePressEvent(self, e):
        if not self.pm or e.button() != Qt.LeftButton:
            return
        pos = e.position()
        self.mode = self._hit(pos) if self.crop else ("new", None)
        self.start = self._to_n(pos)
        self.orig = list(self.crop) if self.crop else None
        if self.mode[0] == "new":
            self.crop = [*self.start, *self.start]

    def mouseMoveEvent(self, e):
        if not self.pm:
            return
        if self.mode is None:
            if self.crop:
                kind, edges = self._hit(e.position())
                if kind == "resize":
                    self.setCursor(Qt.SizeAllCursor if len(edges) == 2 else
                                   Qt.SizeHorCursor if edges & {"l", "r"} else Qt.SizeVerCursor)
                else:
                    self.setCursor(Qt.OpenHandCursor if kind == "move" else Qt.CrossCursor)
            else:
                self.setCursor(Qt.CrossCursor)
            return
        x, y = self._to_n(e.position())
        kind, edges = self.mode
        if kind == "new":
            self.crop = [min(self.start[0], x), min(self.start[1], y), max(self.start[0], x), max(self.start[1], y)]
        elif kind == "move":
            dx, dy = x - self.start[0], y - self.start[1]
            l, t, r, b = self.orig
            dx = min(max(dx, -l), 1 - r)
            dy = min(max(dy, -t), 1 - b)
            self.crop = [l + dx, t + dy, r + dx, b + dy]
        else:
            c = list(self.orig)
            if "l" in edges: c[0] = min(x, c[2] - 0.02)
            if "r" in edges: c[2] = max(x, c[0] + 0.02)
            if "t" in edges: c[1] = min(y, c[3] - 0.02)
            if "b" in edges: c[3] = max(y, c[1] + 0.02)
            self.crop = c
        self.update()

    def mouseReleaseEvent(self, _e):
        self.mode = None
        if self.crop and (self.crop[2] - self.crop[0] < 0.02 or self.crop[3] - self.crop[1] < 0.02):
            self.crop = None
        self.update()


class EditorDialog(QDialog):
    """Girar y recortar una foto. No toca el archivo: devuelve (giro, recorte) y se aplica al guardar."""

    def __init__(self, parent, path, rot=0, crop=None):
        super().__init__(parent)
        self.setWindowTitle("Editar foto")
        self.resize(900, 760)
        self.path, self.rot = path, rot
        self.base = load_scaled(path, 1600)
        self.view = CropView()
        self.view.crop = list(crop) if crop else None
        self._reload()
        row = QHBoxLayout()
        for text, fn in (("⟲ Girar izquierda", lambda: self._rotate(-90)), ("⟳ Girar derecha", lambda: self._rotate(90)),
                         ("Quitar recorte", self._clear_crop), ("Restaurar todo", self._reset)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch()
        hint = QLabel("Arrastra sobre la foto para recortar. Mueve el recuadro o estira sus bordes. "
                      "El original se guarda intacto en fotos/<SKU>/original/.")
        hint.setStyleSheet("color:#9a9996")
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(row)
        lay.addWidget(self.view, 1)
        lay.addWidget(hint)
        lay.addWidget(bb)

    def _reload(self):
        self.view.set_image(apply_edit(self.base, self.rot, None))

    def _rotate(self, deg):
        self.rot = (self.rot + deg) % 360
        self.view.crop = None  # el recorte ya no corresponde a la imagen girada
        self._reload()

    def _clear_crop(self):
        self.view.crop = None
        self.view.update()

    def _reset(self):
        self.rot = 0
        self.view.crop = None
        self._reload()

    def result_edit(self):
        crop = tuple(self.view.crop) if self.view.crop else None
        return self.rot % 360, crop


class DestDialog(QDialog):
    """Elige la carpeta de destino y el nombre del CSV (nuevo o ya existente en esa carpeta)."""

    def __init__(self, parent, start):
        super().__init__(parent)
        self.setWindowTitle("Destino: carpeta y CSV")
        self.setMinimumWidth(520)
        self.folder = QLineEdit(str(start))
        b = QPushButton("Elegir carpeta…")
        b.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.folder, 1)
        row.addWidget(b)
        self.name = QComboBox()
        self.name.setEditable(True)
        self.info = QLabel("")
        self.folder.textChanged.connect(self._refresh)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Carpeta de destino (aquí se crean el CSV y la carpeta «fotos»):"))
        lay.addLayout(row)
        lay.addWidget(QLabel("Nombre del CSV (elige uno existente o escribe uno nuevo):"))
        lay.addWidget(self.name)
        lay.addWidget(self.info)
        lay.addWidget(bb)
        self._refresh()

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Carpeta de destino", self.folder.text() or str(Path.home()))
        if d:
            self.folder.setText(d)

    def _refresh(self):
        d = Path(self.folder.text().strip()).expanduser()
        keep = self.name.currentText()
        self.name.clear()
        found = sorted(p.name for p in d.glob("*.csv")) if d.is_dir() else []
        self.name.addItems(found)
        self.name.setEditText(keep or (found[0] if found else "catalogo"))
        self.info.setText(f"{len(found)} CSV en la carpeta" if d.is_dir() else "La carpeta se creará al guardar")

    def csv_path(self):
        n = self.name.currentText().strip() or "catalogo"
        if not n.lower().endswith(".csv"):
            n += ".csv"
        return Path(self.folder.text().strip()).expanduser() / Path(n).name


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("gatobras")
        self.resize(1300, 900)
        self.cfg = core.load_config()
        self.store = None
        self.folder = None
        self.last_action = None
        self.loader = Loader()
        self.loader.ready.connect(self._thumb_ready)
        self.foto_w = self.foto_h = 0
        self._confirm_key = None
        self.edits = {}  # ruta -> (giro, recorte)
        self._build()
        if self.cfg.get("last_csv"):
            self._open_csv(self.cfg["last_csv"], quiet=True)
        if self.cfg.get("last_folder") and Path(self.cfg["last_folder"]).is_dir():
            self._open_folder(self.cfg["last_folder"])

    # ---------- construcción ----------
    def _build(self):
        def path_label():
            l = QLabel("(sin elegir)")
            l.setWordWrap(True)
            l.setTextInteractionFlags(Qt.TextSelectableByMouse)
            l.setStyleSheet("font-weight:bold; background:transparent")
            return l

        def thumbs():
            w = QListWidget()
            w.setViewMode(QListWidget.IconMode)
            w.setResizeMode(QListWidget.Adjust)
            w.setMovement(QListWidget.Static)
            w.setWordWrap(True)
            w.setIconSize(QSize(LIST_THUMB, LIST_THUMB))
            w.setGridSize(QSize(LIST_THUMB + 24, LIST_THUMB + 36))
            return w

        # izquierda: origen + fotos pendientes
        b_folder = QPushButton("Elegir carpeta de fotos…")
        b_folder.clicked.connect(self.pick_folder)
        self.lbl_folder = path_label()
        self.listw = thumbs()
        self.listw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.listw.currentItemChanged.connect(self._show_current)
        g_src = QGroupBox("1. De dónde vienen las fotos")
        QVBoxLayout(g_src).addWidget(b_folder)
        g_src.layout().addWidget(self.lbl_folder)
        self.g_pend = QGroupBox("Fotos pendientes")
        QVBoxLayout(self.g_pend).addWidget(self.listw)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(g_src)
        lv.addWidget(self.g_pend, 1)

        # centro: foto actual + datos
        self.preview = Preview()
        self.warn = QLabel("")
        self.warn.setStyleSheet("color:#f8e45c; background:transparent")
        self.f = {}
        main_spec = [("nombre", "Nombre"), ("artista", "Artista"), ("alto_cm", "Alto cm"), ("ancho_cm", "Ancho cm")]
        extra_spec = [("sku", "SKU"), ("anio", "Año"), ("tecnica", "Técnica"), ("tipo", "Tipo"),
                      ("fondo_cm", "Fondo cm"), ("notas", "Notas")]
        form = QGridLayout()
        for i, (key, label) in enumerate(main_spec):
            w = QLineEdit()
            w.setStyleSheet("font-size:17px")
            self.f[key] = w
            form.addWidget(QLabel(label), 0, i)
            form.addWidget(w, 1, i)
        extra = QGridLayout()
        for i, (key, label) in enumerate(extra_spec):
            w = QComboBox() if key == "tipo" else QLineEdit()
            if key == "tipo":
                w.setEditable(True)
                w.addItems(TIPOS)
            self.f[key] = w
            extra.addWidget(QLabel(label), i // 3, (i % 3) * 2)
            extra.addWidget(w, i // 3, (i % 3) * 2 + 1)
        # Enter avanza al siguiente campo; Enter en «ancho» guarda y pasa a la siguiente foto
        order = ["nombre", "artista", "alto_cm", "ancho_cm"]
        for cur, nxt in zip(order, order[1:]):
            self.f[cur].returnPressed.connect(lambda n=nxt: self._focus(n))
        self.f["ancho_cm"].returnPressed.connect(self._enter_save)
        for k in ("alto_cm", "ancho_cm"):
            self.f[k].editingFinished.connect(self._auto_order)
        self.f["notas"].returnPressed.connect(self.save_selected)
        swap = QPushButton("⇄ alto/ancho")
        swap.clicked.connect(self._swap)
        form.addWidget(swap, 1, 4)

        self.b_edit = QPushButton("✂  Girar / recortar foto…")
        self.b_edit.setShortcut("Ctrl+E")
        self.b_edit.clicked.connect(self.edit_photo)
        self.b_save = QPushButton("Guardar y siguiente")
        self.b_save.setObjectName("primary")
        self.b_save.clicked.connect(self.save_selected)
        self.b_add = QPushButton("Agregar a obra existente…")
        self.b_add.clicked.connect(self.add_existing)
        self.b_undo = QPushButton("Deshacer último guardado")
        self.b_undo.clicked.connect(self.undo)
        self.b_undo.setEnabled(False)
        btns = QHBoxLayout()
        for b in (self.b_save, self.b_add, self.b_undo):
            btns.addWidget(b)
        g_form = QGroupBox("Datos de la obra")
        fl = QVBoxLayout(g_form)
        fl.addWidget(self.warn)
        fl.addLayout(form)
        g_extra = QGroupBox("Otros datos (opcional)")
        g_extra.setLayout(extra)
        fl.addWidget(g_extra)
        fl.addLayout(btns)
        mid = QWidget()
        mv = QVBoxLayout(mid)
        mv.addWidget(self.preview, 1)
        mv.addWidget(self.b_edit)
        mv.addWidget(g_form)

        # derecha: destino + fotos ya catalogadas
        b_csv = QPushButton("Elegir carpeta de destino y CSV…")
        b_csv.clicked.connect(self.pick_csv)
        self.lbl_csv = path_label()
        self.lbl_csv_name = QLabel("")
        self.prefix = QLineEdit(self.cfg.get("prefix", "CUA"))
        self.prefix.setMaximumWidth(70)
        self.prefix.editingFinished.connect(self._prefix_changed)
        pr = QHBoxLayout()
        pr.addWidget(QLabel("Prefijo SKU:"))
        pr.addWidget(self.prefix)
        pr.addStretch()
        g_dst = QGroupBox("2. A dónde van (carpeta + CSV)")
        dl = QVBoxLayout(g_dst)
        for w in (b_csv, self.lbl_csv, self.lbl_csv_name):
            dl.addWidget(w)
        dl.addLayout(pr)
        self.destw = thumbs()
        self.destw.setSelectionMode(QAbstractItemView.NoSelection)
        self.g_done = QGroupBox("Ya en el destino")
        QVBoxLayout(self.g_done).addWidget(self.destw)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.addWidget(g_dst)
        rv.addWidget(self.g_done, 1)

        split = QSplitter()
        for w in (left, mid, right):
            split.addWidget(w)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)
        split.setStretchFactor(2, 2)
        split.setSizes([380, 540, 380])

        # pestaña CSV
        self.table = QTableWidget()
        self.table.itemChanged.connect(self._cell_edited)
        b_open = QPushButton("Abrir CSV con el programa por defecto")
        b_open.clicked.connect(self.open_csv_external)
        b_reload = QPushButton("Recargar")
        b_reload.clicked.connect(self.fill_table)
        tbtn = QHBoxLayout()
        tbtn.addWidget(b_open)
        tbtn.addWidget(b_reload)
        tbtn.addStretch()
        tab2 = QWidget()
        lay2 = QVBoxLayout(tab2)
        lay2.addLayout(tbtn)
        lay2.addWidget(self.table)

        self.tabs = QTabWidget()
        self.tabs.addTab(split, "Catalogar")
        self.tabs.addTab(tab2, "CSV")
        self.tabs.currentChanged.connect(lambda i: self.fill_table() if i == 1 else None)

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        b_upd = QPushButton("Actualizar gatobras")
        b_upd.setToolTip("Descarga la última versión desde GitHub")
        b_upd.clicked.connect(self.update_app)
        self.statusBar().addPermanentWidget(b_upd)
        self.statusBar().showMessage("Listo")

    # ---------- carpeta y CSV ----------
    def pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Carpeta de fotos", self.cfg.get("last_folder", str(Path.home())))
        if d:
            self._open_folder(d)

    def _open_folder(self, d):
        self.folder = Path(d)
        self.cfg["last_folder"] = d
        core.save_config(self.cfg)
        self.lbl_folder.setText(d)
        self.lbl_folder.setToolTip(d)
        self.refresh_list()

    def pick_csv(self):
        last = self.cfg.get("last_csv")
        dlg = DestDialog(self, Path(last).parent if last else Path.home())
        if last:
            dlg.name.setEditText(Path(last).name)
        if dlg.exec():
            self._open_csv(dlg.csv_path())

    def _open_csv(self, path, quiet=False):
        try:
            self.store = core.Store(path)
        except (OSError, UnicodeDecodeError, Exception) as e:
            if not quiet:
                QMessageBox.critical(self, "CSV", f"No se pudo abrir el CSV:\n{e}")
            return
        self.cfg["last_csv"] = str(path)
        core.save_config(self.cfg)
        self.lbl_csv.setToolTip(str(path))
        self._update_dest_labels()
        self.last_action = None
        self.b_undo.setEnabled(False)
        self._suggest_sku()

    def _update_dest_labels(self):
        st = self.store
        self.lbl_csv.setText(str(st.root))
        self.lbl_csv_name.setText(f"CSV: {st.path.name}" + ("" if st.path.exists() else " (se crea al guardar)")
                                  + f" · {len(st.rows)} obras")
        self.destw.clear()
        for row in reversed(st.rows):  # la última guardada arriba
            p = st.root / row["ruta_foto"] if row.get("ruta_foto") else st.first_photo(row["sku"])
            if p and Path(p).is_file():
                it = QListWidgetItem(row["sku"])
                it.setToolTip(row.get("nombre", ""))
                it.setData(Qt.UserRole, str(p))
                self.destw.addItem(it)
                self._set_icon(it)
        self.g_done.setTitle(f"Ya en el destino ({self.destw.count()})")

    def _prefix_changed(self):
        self.cfg["prefix"] = self.prefix.text().strip() or "CUA"
        core.save_config(self.cfg)
        self._suggest_sku()

    def _suggest_sku(self):
        if self.store:
            self.f["sku"].setText(self.store.next_sku(self.prefix.text().strip() or "CUA"))

    # ---------- lista y preview ----------
    def refresh_list(self):
        self.listw.clear()
        if not self.folder:
            return
        try:
            imgs = core.list_images(self.folder)
        except OSError as e:
            QMessageBox.critical(self, "Carpeta", str(e))
            return
        for p in imgs:
            it = QListWidgetItem(p.name)
            it.setData(Qt.UserRole, str(p))
            self.listw.addItem(it)
            self._set_icon(it)
        if imgs:
            self.listw.setCurrentRow(0)
        else:
            self.preview.set_image(None, "No hay fotos JPG/PNG en la carpeta")
        self.statusBar().showMessage(f"{len(imgs)} fotos pendientes")
        self.g_pend.setTitle(f"Fotos pendientes ({len(imgs)})")

    def _set_icon(self, item):
        pm = self.loader.get(item.data(Qt.UserRole), LIST_THUMB)
        if pm:
            item.setIcon(QIcon(pm))

    def _thumb_ready(self, path, side, _img):
        if side == LIST_THUMB:
            for lw in (self.listw, self.destw):
                for i in range(lw.count()):
                    it = lw.item(i)
                    if it.data(Qt.UserRole) == path:
                        self._set_icon(it)
                        break
        elif side == TABLE_THUMB:
            for r in range(self.table.rowCount()):
                lbl = self.table.cellWidget(r, 0)
                if lbl is not None and lbl.property("path") == path:
                    lbl.setPixmap(self.loader.cache[(path, side)])
        elif side == PREVIEW_SIDE:
            cur = self.listw.currentItem()
            if cur and cur.data(Qt.UserRole) == path:
                self._show_current(cur)

    def _show_current(self, item, _prev=None):
        if item is None:
            return
        path = item.data(Qt.UserRole)
        pm = self.loader.get(path, PREVIEW_SIDE)
        if pm is None:
            self.preview.set_image(None, "Cargando…")
            return
        img = pm.toImage()
        if path in self.edits:
            img = apply_edit(img, *self.edits[path])
        self.foto_w, self.foto_h = img.width(), img.height()
        self.preview.set_image(img)
        self._auto_order()

    def edit_photo(self):
        cur = self.listw.currentItem()
        if cur is None:
            return
        path = cur.data(Qt.UserRole)
        rot, crop = self.edits.get(path, (0, None))
        dlg = EditorDialog(self, path, rot, crop)
        if not dlg.exec():
            return
        rot, crop = dlg.result_edit()
        name = Path(path).name
        if rot == 0 and crop is None:
            self.edits.pop(path, None)
            cur.setText(name)
        else:
            self.edits[path] = (rot, crop)
            cur.setText(name + " ✎")
        self._show_current(cur)

    def _render_edit(self, path):
        """Genera la foto editada (a resolución completa) en una carpeta temporal junto al CSV."""
        rot, crop = self.edits[path]
        r = QImageReader(str(path))
        r.setAutoTransform(True)
        img = r.read()
        if img.isNull():
            raise GatoError(f"No se pudo leer {Path(path).name} para editarla")
        img = apply_edit(img, rot, crop)
        tmpdir = self.store.root / ".gatobras-tmp"
        tmpdir.mkdir(parents=True, exist_ok=True)
        out = tmpdir / Path(path).name
        ok = img.save(str(out), None, 95) if out.suffix.lower() in (".jpg", ".jpeg") else img.save(str(out))
        if not ok:
            raise GatoError(f"No se pudo guardar la foto editada de {Path(path).name}")
        return out

    def _processed(self, path):
        return self._render_edit(path) if path in self.edits else None

    def _cleanup_tmp(self):
        try:
            (self.store.root / ".gatobras-tmp").rmdir()
        except OSError:
            pass

    # ---------- medidas ----------
    def _auto_order(self):
        try:
            a, b = core.parse_num(self.f["alto_cm"].text()), core.parse_num(self.f["ancho_cm"].text())
        except GatoError as e:
            self.warn.setText(str(e))
            return
        if (a is None) != (b is None):
            return  # solo una medida: se conserva el aviso de «falta…» si lo hay
        self.warn.setText("")
        if a is None:
            return
        msg = core.check_dims(a, b, self.foto_w, self.foto_h) or ""
        if msg and self._confirm_key == self._dims_key():
            msg += " — pulsa Enter otra vez para guardar así"
        self.warn.setText(msg)

    def _dims_key(self):
        cur = self.listw.currentItem()
        return (cur.data(Qt.UserRole) if cur else None, self.f["alto_cm"].text(), self.f["ancho_cm"].text())

    def _focus(self, key):
        self.f[key].setFocus(Qt.TabFocusReason)

    def _enter_save(self):
        """Enter en «ancho»: si hay aviso de medidas, el primer Enter solo avisa y el segundo guarda."""
        try:
            a, b = core.parse_num(self.f["alto_cm"].text()), core.parse_num(self.f["ancho_cm"].text())
        except GatoError:
            a = b = None
        key = self._dims_key()
        if core.check_dims(a, b, self.foto_w, self.foto_h) and self._confirm_key != key \
                and len(self.listw.selectedItems()) <= 1:
            self._confirm_key = key
            self._auto_order()
            return
        self._auto_order()
        self.save_selected()

    def _swap(self):
        a, b = self.f["alto_cm"].text(), self.f["ancho_cm"].text()
        self.f["alto_cm"].setText(b)
        self.f["ancho_cm"].setText(a)
        self.warn.setText("")

    # ---------- acciones ----------
    def _form_data(self):
        data = {}
        for k, w in self.f.items():
            if k == "sku":
                continue
            data[k] = (w.currentText() if isinstance(w, QComboBox) else w.text()).strip()
        data["precio"] = ""
        for k in ("alto_cm", "ancho_cm", "fondo_cm"):
            n = core.parse_num(data[k])
            data[k] = core.fmt_num(n)
        return data

    def _targets(self):
        sel = self.listw.selectedItems()
        if not sel and self.listw.currentItem():
            sel = [self.listw.currentItem()]
        return sorted(sel, key=lambda i: self.listw.row(i))

    def _ready(self):
        if not self.store:
            QMessageBox.information(self, "gatobras", "Primero elige el CSV de destino.")
            return False
        return True

    def save_selected(self):
        if not self._ready():
            return
        targets = self._targets()
        if not targets:
            return
        try:
            data = self._form_data()
        except GatoError as e:
            QMessageBox.warning(self, "Datos", str(e))
            return
        falta = [k for k in ("alto_cm", "ancho_cm") if not data[k]]
        if len(falta) == 1:
            nom = "alto" if falta[0] == "alto_cm" else "ancho"
            self.warn.setText(f"Falta el {nom}: pon las dos medidas o deja las dos vacías.")
            self._focus(falta[0])
            return
        prefix = self.prefix.text().strip() or "CUA"
        action, error = core.Action(), None
        for n, it in enumerate(targets):
            sku = self.f["sku"].text().strip() if n == 0 else self.store.next_sku(prefix)
            try:
                action.items.append(self.store.add_new(it.data(Qt.UserRole), sku, data, self._processed(it.data(Qt.UserRole))))
            except GatoError as e:
                error = str(e)
                break
        self._cleanup_tmp()
        self._after_change(action, error)

    def add_existing(self):
        if not self._ready():
            return
        targets = self._targets()
        if not targets:
            return
        if not self.store.rows:
            QMessageBox.information(self, "gatobras", "El CSV no tiene obras todavía.")
            return
        labels = [f"{r['sku']} — {r['nombre']}" if r["nombre"] else r["sku"] for r in reversed(self.store.rows)]
        choice, ok = QInputDialog.getItem(self, "Agregar a obra existente", "Obra:", labels, 0, False)
        if not ok:
            return
        sku = self.store.rows[len(self.store.rows) - 1 - labels.index(choice)]["sku"]
        action, error = core.Action(), None
        for it in targets:
            try:
                action.items.append(self.store.add_to_existing(it.data(Qt.UserRole), sku, self._processed(it.data(Qt.UserRole))))
            except GatoError as e:
                error = str(e)
                break
        self._cleanup_tmp()
        self._after_change(action, error)

    def _after_change(self, action, error):
        if action.items:
            self.last_action = action
            self.b_undo.setEnabled(True)
            skus = ", ".join(i.sku for i in action.items)
            self.statusBar().showMessage(f"Guardado: {skus}")
            # conserva alto/ancho/fondo; limpia el resto
            keep = {"alto_cm", "ancho_cm", "fondo_cm"}
            for k, w in self.f.items():
                if k not in keep:
                    w.setCurrentText("") if isinstance(w, QComboBox) else w.setText("")
            self._remove_done(action)
            self._update_dest_labels()
        self._suggest_sku()
        self._focus("nombre")
        if error:
            QMessageBox.warning(self, "No se guardó todo", error)

    def _remove_done(self, action):
        done = {str(i.src) for i in action.items}
        for d in done:
            self.edits.pop(d, None)
        first = None
        for r in reversed(range(self.listw.count())):
            if self.listw.item(r).data(Qt.UserRole) in done:
                self.listw.takeItem(r)
                first = r
        if self.listw.count():
            self.listw.setCurrentRow(min(first or 0, self.listw.count() - 1))
        else:
            self.preview.set_image(None, "No quedan fotos en la carpeta")
        self.g_pend.setTitle(f"Fotos pendientes ({self.listw.count()})")

    def undo(self):
        if not (self.store and self.last_action):
            return
        n = len(self.last_action.items)
        if QMessageBox.question(self, "Deshacer", f"¿Devolver {n} foto(s) a su lugar y quitar sus filas del CSV?") \
                != QMessageBox.Yes:
            return
        try:
            self.store.undo(self.last_action)
        except GatoError as e:
            QMessageBox.warning(self, "Deshacer", str(e))
        self.last_action = None
        self.b_undo.setEnabled(False)
        self._update_dest_labels()
        self.refresh_list()
        self._suggest_sku()
        self.statusBar().showMessage("Deshecho")

    # ---------- vista del CSV ----------
    def fill_table(self):
        """Llena la tabla por tandas (la ventana no se congela con CSV grandes)."""
        t = self.table
        self._fill_gen = getattr(self, "_fill_gen", 0) + 1
        t.blockSignals(True)
        t.clear()
        if not self.store:
            t.setRowCount(0)
            t.blockSignals(False)
            return
        cols = self.store.columns
        t.setColumnCount(len(cols) + 1)
        t.setHorizontalHeaderLabels(["foto"] + cols)
        t.setRowCount(len(self.store.rows))
        t.verticalHeader().setDefaultSectionSize(TABLE_THUMB + 10)
        t.setColumnWidth(0, TABLE_THUMB + 10)
        t.blockSignals(False)
        self._fill_chunk(self._fill_gen, 0)

    def _fill_chunk(self, gen, start, size=15):
        if gen != self._fill_gen or not self.store:
            return
        t, cols, rows = self.table, self.store.columns, self.store.rows
        end = min(start + size, len(rows))
        t.blockSignals(True)
        for r in range(start, end):
            row = rows[r]
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignCenter)
            p = self.store.root / row["ruta_foto"] if row.get("ruta_foto") else self.store.first_photo(row["sku"])
            if p and Path(p).is_file():
                lbl.setProperty("path", str(p))
                pm = self.loader.get(p, TABLE_THUMB)
                if pm:
                    lbl.setPixmap(pm)
            t.setCellWidget(r, 0, lbl)
            for c, col in enumerate(cols, start=1):
                it = QTableWidgetItem(row.get(col, ""))
                if col in core.READONLY:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                t.setItem(r, c, it)
        t.blockSignals(False)
        if end < len(rows):
            self.statusBar().showMessage(f"Cargando CSV… {end}/{len(rows)}")
            QTimer.singleShot(0, lambda: self._fill_chunk(gen, end, size))
        else:
            self.statusBar().showMessage(f"CSV: {len(rows)} obras")

    def _cell_edited(self, item):
        if not self.store or item.column() == 0:
            return
        sku = self.table.item(item.row(), self.store.columns.index("sku") + 1).text()
        col = self.store.columns[item.column() - 1]
        try:
            self.store.update_cell(sku, col, item.text())
            self.statusBar().showMessage(f"{sku}: {col} actualizado")
        except Exception as e:
            QMessageBox.warning(self, "CSV", str(e))

    def update_app(self):
        self.statusBar().showMessage("Actualizando…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            msg = core.update_app()
        except GatoError as e:
            QMessageBox.warning(self, "Actualizar", str(e))
            self.statusBar().showMessage("Falló la actualización")
            return
        finally:
            QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Actualizar", f"{msg}\n\nCierra y vuelve a abrir gatobras para ver los cambios.")
        self.statusBar().showMessage("Actualizado; reinicia la app")

    def open_csv_external(self):
        if self.store and self.store.path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.path)))
        else:
            QMessageBox.information(self, "gatobras", "El CSV todavía no existe (se crea al guardar la primera obra).")


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setApplicationName("gatobras")
    app.setDesktopFileName("gatobras")
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent.parent / "assets" / "gatobras.svg")))
    w = MainWindow()
    w.show()
    app.exec()
