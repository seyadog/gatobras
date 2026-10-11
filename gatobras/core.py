"""Lógica de gatobras sin interfaz: CSV, SKU, mover fotos, deshacer, medidas."""
import csv
import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png"}
CONFIG_DIR = Path.home() / "Documents" / "PolluxData" / "gatobras_config"
CONFIG_FILE = CONFIG_DIR / "config.json"

FIELDS = ["sku", "nombre", "artista", "anio", "tecnica", "tipo", "alto_cm", "ancho_cm",
          "fondo_cm", "precio", "fotos", "ruta_foto", "archivo_original", "notas"]
READONLY = {"sku", "fotos", "ruta_foto", "archivo_original"}


class GatoError(Exception):
    pass


# ---------- configuración ----------

def load_config():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


# ---------- medidas ----------

def parse_num(text):
    text = (text or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        raise GatoError(f"«{text}» no es un número")


def fmt_num(x):
    if x is None:
        return ""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def order_dims(a, b, foto_w, foto_h):
    """Decide alto y ancho de la obra según la forma de la foto (ya con EXIF aplicado).

    Devuelve (alto, ancho, aviso). El aviso es None o un texto si hay duda.
    """
    if a is None or b is None:
        return a, b, None
    hi, lo = max(a, b), min(a, b)
    casi_cuadrada = lo > 0 and hi / lo < 1.08
    foto_cuadrada = foto_w and foto_h and abs(foto_w - foto_h) / max(foto_w, foto_h) < 0.05
    if casi_cuadrada or foto_cuadrada:
        return a, b, "Obra casi cuadrada: revisa cuál es alto y cuál ancho (botón ⇄)"
    if not foto_w or not foto_h:
        return a, b, None
    if foto_w >= foto_h:
        return lo, hi, None
    return hi, lo, None


def check_dims(alto, ancho, foto_w, foto_h):
    """Solo avisa (no cambia nada) si alto/ancho no cuadran con la forma de la foto. Devuelve texto o None."""
    if alto is None or ancho is None or not foto_w or not foto_h:
        return None
    hi, lo = max(alto, ancho), min(alto, ancho)
    if lo > 0 and hi / lo < 1.08 or abs(foto_w - foto_h) / max(foto_w, foto_h) < 0.05:
        return None  # casi cuadrada: no hay forma de saber cuál es cuál, no se avisa
    if (foto_w > foto_h) != (ancho > alto):
        forma = "horizontal" if foto_w > foto_h else "vertical"
        return f"Ojo: la foto es {forma} pero las medidas dicen lo contrario (¿foto girada? si está bien, ignora esto)"
    return None


# ---------- archivos ----------

def list_images(folder):
    return sorted((p for p in Path(folder).iterdir()
                   if p.is_file() and p.suffix.lower() in IMG_EXT), key=lambda p: p.name.lower())


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_move(src, dst):
    """Mueve sin sobrescribir nunca. Entre sistemas de archivos: copia, verifica y recién borra."""
    src, dst = Path(src), Path(dst)
    if not src.is_file():
        raise GatoError(f"No existe la foto de origen: {src}")
    if dst.exists():
        raise GatoError(f"Ya existe el destino, no se sobrescribe: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(src, dst)
        return
    except OSError as e:
        if e.errno != 18:  # EXDEV: otro sistema de archivos
            raise GatoError(f"No se pudo mover {src.name}: {e}")
    tmp = dst.with_name(dst.name + ".part")
    if tmp.exists():
        raise GatoError(f"Quedó un archivo temporal: {tmp}")
    try:
        shutil.copy2(src, tmp)
        if tmp.stat().st_size != src.stat().st_size or _sha256(tmp) != _sha256(src):
            raise GatoError(f"La copia de {src.name} no coincide con el original; no se borró nada")
        os.rename(tmp, dst)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    src.unlink()


# ---------- CSV ----------

@dataclass
class Item:
    sku: str
    src: Path
    dest: Path
    new_row: bool
    created_dir: bool = False
    prev_fotos: str = ""
    prev_ruta: str = ""
    orig_dest: Path = None  # si la foto fue editada: dónde quedó el original intacto


@dataclass
class Action:
    items: list = field(default_factory=list)


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.root = self.path.parent
        self.columns = []
        self.rows = []
        self._backed_up = False
        if self.path.exists():
            self.load()
        self.columns += [c for c in FIELDS if c not in self.columns]
        for r in self.rows:
            for c in self.columns:
                r.setdefault(c, "")
            if not r["ruta_foto"] and r["sku"]:
                p = self.first_photo(r["sku"])
                if p:
                    r["ruta_foto"] = p.relative_to(self.root).as_posix()

    def load(self):
        with open(self.path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.columns = list(reader.fieldnames or [])
            self.rows = [{k: (v or "") for k, v in row.items() if k is not None} for row in reader]

    def save(self):
        if self.path.exists() and not self._backed_up:
            shutil.copy2(self.path, self.path.with_name(self.path.name + ".bak"))
        self._backed_up = True
        self.root.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.root, prefix=".gatobras-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=self.columns, lineterminator="\n")
                w.writeheader()
                w.writerows(self.rows)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except Exception:
            Path(tmp).unlink(missing_ok=True)
            raise

    # --- consultas ---
    def find(self, sku):
        return next((r for r in self.rows if r["sku"] == sku), None)

    def photos_dir(self, sku):
        return self.root / "fotos" / sku

    def first_photo(self, sku):
        d = self.photos_dir(sku)
        if d.is_dir():
            for p in sorted(d.iterdir()):
                if p.stem == "1" and p.suffix.lower() in IMG_EXT:
                    return p
        return None

    def next_sku(self, prefix):
        pat = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
        nums = [int(m.group(1)) for r in self.rows if (m := pat.match(r["sku"]))]
        fotos = self.root / "fotos"
        if fotos.is_dir():
            nums += [int(m.group(1)) for p in fotos.iterdir() if (m := pat.match(p.name))]
        return f"{prefix}-{max(nums, default=0) + 1:03d}"

    # --- operaciones ---
    @staticmethod
    def _place(src, folder, n, processed):
        """Coloca la foto como <n>.<ext>. Con `processed`: la editada va ahí y el original a original/."""
        if processed is None:
            dest = folder / f"{n}{src.suffix.lower()}"
            safe_move(src, dest)
            return dest, None
        processed = Path(processed)
        dest = folder / f"{n}{processed.suffix.lower()}"
        orig_dest = folder / "original" / f"{n}_{src.name}"
        if dest.exists() or orig_dest.exists():
            raise GatoError(f"Ya existe el destino, no se sobrescribe: {dest}")
        safe_move(processed, dest)
        try:
            safe_move(src, orig_dest)
        except Exception:
            safe_move(dest, processed)
            raise
        return dest, orig_dest

    @staticmethod
    def _unplace(src, dest, orig_dest):
        """Inverso de _place. Con original guardado: lo devuelve y borra solo la copia editada."""
        if orig_dest is None:
            safe_move(dest, src)
            return
        safe_move(orig_dest, src)
        Path(dest).unlink(missing_ok=True)

    def add_new(self, src, sku, data, processed=None):
        """Mueve la foto a fotos/<sku>/1.<ext> y agrega la fila. Devuelve un Item (para deshacer).

        Si `processed` (foto editada) viene dado, ese archivo queda como 1.<ext> y el original
        se guarda intacto en fotos/<sku>/original/."""
        src = Path(src)
        sku = sku.strip()
        if not sku or re.search(r"[\\/\s]", sku):
            raise GatoError(f"SKU inválido: «{sku}»")
        if self.find(sku) or self.photos_dir(sku).exists():
            raise GatoError(f"El SKU {sku} ya existe; no se reutiliza")
        dest, orig_dest = self._place(src, self.photos_dir(sku), 1, processed)
        row = {c: "" for c in self.columns}
        row.update({k: v for k, v in data.items() if k in row})
        row.update(sku=sku, fotos="1", ruta_foto=dest.relative_to(self.root).as_posix(),
                   archivo_original=src.name)
        self.rows.append(row)
        try:
            self.save()
        except Exception as e:
            self.rows.pop()
            self._unplace(src, dest, orig_dest)
            for d in (dest.parent / "original", dest.parent):
                try:
                    d.rmdir()
                except OSError:
                    pass
            raise GatoError(f"No se pudo escribir el CSV; la foto volvió a su lugar: {e}")
        return Item(sku, src, dest, new_row=True, created_dir=True, orig_dest=orig_dest)

    def add_to_existing(self, src, sku, processed=None):
        src = Path(src)
        row = self.find(sku)
        if row is None:
            raise GatoError(f"No existe el SKU {sku}")
        folder = self.photos_dir(sku)
        created = not folder.exists()
        nums = [int(p.stem) for p in folder.iterdir() if p.stem.isdigit()] if folder.is_dir() else []
        n = max(nums, default=0) + 1
        dest, orig_dest = self._place(src, folder, n, processed)
        item = Item(sku, src, dest, new_row=False, created_dir=created,
                    prev_fotos=row["fotos"], prev_ruta=row["ruta_foto"], orig_dest=orig_dest)
        row["fotos"] = str(sum(1 for p in folder.iterdir() if p.suffix.lower() in IMG_EXT))
        if not row["ruta_foto"]:
            row["ruta_foto"] = dest.relative_to(self.root).as_posix()
        try:
            self.save()
        except Exception as e:
            row["fotos"], row["ruta_foto"] = item.prev_fotos, item.prev_ruta
            self._unplace(src, dest, orig_dest)
            raise GatoError(f"No se pudo escribir el CSV; la foto volvió a su lugar: {e}")
        return item

    def undo(self, action):
        errors = []
        for it in reversed(action.items):
            try:
                self._unplace(it.src, it.dest, it.orig_dest)
            except GatoError as e:
                errors.append(str(e))
                continue
            row = self.find(it.sku)
            if it.new_row:
                if row in self.rows:
                    self.rows.remove(row)
            elif row is not None:
                row["fotos"], row["ruta_foto"] = it.prev_fotos, it.prev_ruta
            for d in ((it.dest.parent / "original", it.dest.parent) if it.created_dir else (it.dest.parent / "original",)):
                try:
                    d.rmdir()
                except OSError:
                    pass
        self.save()
        if errors:
            raise GatoError("No se pudo deshacer todo:\n" + "\n".join(errors))

    def update_cell(self, sku, col, value):
        row = self.find(sku)
        if row is None or col in READONLY:
            raise GatoError("Celda no editable")
        row[col] = value
        self.save()


# ---------- actualización ----------
REPO = "seyadog/gatobras"
APP_ROOT = Path(__file__).resolve().parent.parent


def update_app(root=APP_ROOT):
    """Actualiza el código desde GitHub. Devuelve un mensaje. No toca .venv, datos ni configuración.

    En un clon de git hace `git pull --ff-only`; si no, baja el tarball de `main` y copia encima.
    """
    import subprocess
    import tarfile
    import urllib.request

    root = Path(root)
    if (root / ".git").exists():
        r = subprocess.run(["git", "-C", str(root), "pull", "--ff-only"], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise GatoError("git pull falló:\n" + (r.stderr or r.stdout).strip())
        return r.stdout.strip() or "Listo."
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/tarball/main",
                                 headers={"User-Agent": "gatobras"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, tempfile.TemporaryDirectory() as tmp:
            tf = tarfile.open(fileobj=resp, mode="r|gz")
            tf.extractall(tmp, filter="data")
            src = next(Path(tmp).iterdir())
            for p in src.rglob("*"):
                if p.is_file():
                    dest = root / p.relative_to(src)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dest)
    except GatoError:
        raise
    except Exception as e:
        raise GatoError(f"No se pudo actualizar: {e}")
    return "Código actualizado."
