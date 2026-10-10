import csv
import tempfile
import unittest
from pathlib import Path

from gatobras import core

OLD = "sku,nombre,alto_cm,ancho_cm,fondo_cm,fotos,archivo_original,notas,extra\nCUA-001,Cuadro CUA-001,82.6,54.9,,1,IMG_0006.jpg,,x\n"


class CoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.dest = self.tmp / "dest"
        self.dest.mkdir()
        self.src = self.tmp / "src"
        self.src.mkdir()
        for n in ("a.JPG", "b.png", "c.jpg"):
            (self.src / n).write_bytes(n.encode() * 10)

    def rows(self, p):
        with open(p, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_flow_with_existing_csv(self):
        p = self.dest / "c.csv"
        p.write_text(OLD, encoding="utf-8")
        s = core.Store(p)
        self.assertEqual(s.next_sku("CUA"), "CUA-002")
        it = s.add_new(self.src / "a.JPG", "CUA-002", {"nombre": "Uno, con coma", "alto_cm": "10"})
        self.assertTrue((self.dest / "fotos/CUA-002/1.jpg").is_file())
        self.assertFalse((self.src / "a.JPG").exists())
        rows = self.rows(p)
        self.assertEqual(rows[0]["extra"], "x")  # columna desconocida preservada
        self.assertEqual(rows[1]["nombre"], "Uno, con coma")
        self.assertEqual(rows[1]["ruta_foto"], "fotos/CUA-002/1.jpg")
        self.assertTrue((self.dest / "c.csv.bak").exists())
        # agregar a existente
        it2 = s.add_to_existing(self.src / "b.png", "CUA-002")
        self.assertTrue((self.dest / "fotos/CUA-002/2.png").is_file())
        self.assertEqual(self.rows(p)[1]["fotos"], "2")
        # deshacer en orden inverso
        s.undo(core.Action([it2]))
        self.assertTrue((self.src / "b.png").exists())
        self.assertEqual(self.rows(p)[1]["fotos"], "1")
        s.undo(core.Action([it]))
        self.assertTrue((self.src / "a.JPG").exists())
        self.assertEqual(len(self.rows(p)), 1)
        self.assertFalse((self.dest / "fotos/CUA-002").exists())

    def test_never_overwrite_or_reuse(self):
        s = core.Store(self.dest / "n.csv")
        s.add_new(self.src / "a.JPG", "CUA-001", {})
        with self.assertRaises(core.GatoError):
            s.add_new(self.src / "c.jpg", "CUA-001", {})
        self.assertTrue((self.src / "c.jpg").exists())
        self.assertEqual(s.next_sku("CUA"), "CUA-002")

    def test_dims(self):
        self.assertEqual(core.order_dims(80, 50, 4000, 3000)[:2], (50, 80))   # horizontal
        self.assertEqual(core.order_dims(50, 80, 3000, 4000)[:2], (80, 50))   # vertical
        self.assertIsNotNone(core.order_dims(50, 52, 4000, 3000)[2])          # casi cuadrada
        self.assertEqual(core.parse_num("12,5"), 12.5)


if __name__ == "__main__":
    unittest.main()


class EditedPhotoTest(CoreTest):
    def test_edited_keeps_original_and_undo(self):
        p = self.dest / "c.csv"
        s = core.Store(p)
        edited = self.tmp / "edit.jpg"
        edited.write_bytes(b"editada")
        it = s.add_new(self.src / "a.JPG", "CUA-001", {}, processed=edited)
        self.assertEqual((self.dest / "fotos/CUA-001/1.jpg").read_bytes(), b"editada")
        self.assertTrue((self.dest / "fotos/CUA-001/original/1_a.JPG").is_file())
        self.assertFalse((self.src / "a.JPG").exists())
        s.undo(core.Action([it]))
        self.assertTrue((self.src / "a.JPG").is_file())
        self.assertFalse((self.dest / "fotos/CUA-001").exists())
        self.assertEqual(len(self.rows(p)), 0)
