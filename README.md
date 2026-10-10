# gatobras 🐈‍⬛

App de escritorio (Linux, Python + PySide6) para catalogar fotos de obras de arte: eliges de dónde
vienen las fotos y dónde se guardan, llenas unos pocos datos con Enter, y queda todo ordenado en una
carpeta `fotos/` y un CSV. Alimenta el e-commerce de Sarapa.

## Instalar y ejecutar

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./gatobras.sh
```

Para tenerla en el menú de aplicaciones de GNOME: crea `~/.local/share/applications/gatobras.desktop`
con `Exec=<ruta>/gatobras.sh` e `Icon=gatobras`, y copia `assets/gatobras.svg` a
`~/.local/share/icons/hicolor/scalable/apps/`.

## Cómo se usa

La ventana tiene tres columnas:

1. **Izquierda:** carpeta de origen de las fotos y miniaturas de las pendientes.
2. **Centro:** la foto actual y el formulario.
3. **Derecha:** carpeta de destino + nombre del CSV, y miniaturas de lo ya catalogado (la última arriba).

Flujo rápido: **nombre ⏎ artista ⏎ alto ⏎ ancho ⏎** → guarda y pasa a la siguiente foto.

- Todo es opcional, pero si pones una medida (alto o ancho) hay que poner las dos.
- Alto y ancho nunca se reordenan solos. Si no cuadran con la forma de la foto, avisa y pide un segundo
  Enter para guardar. El botón ⇄ las intercambia.
- «Otros datos»: SKU (automático: `CUA-001`, `CUA-002`…), año, técnica, tipo, fondo (grosor del marco), notas.
- Selección múltiple: aplica los mismos datos a varias fotos (un SKU por foto).
- **Agregar a obra existente**: la foto va como `2.jpg`, `3.jpg`… de un SKU ya registrado.
- **Deshacer** el último guardado (devuelve la foto y quita la fila).
- **Girar / recortar** (Ctrl+E): se aplica al guardar; el original queda intacto en `fotos/<SKU>/original/`.
- Pestaña **CSV**: tabla editable con miniaturas, y botón para abrirlo con el programa por defecto.

## Qué se crea en el destino

```
<carpeta de destino>/
├── <nombre>.csv
└── fotos/
    └── CUA-001/
        ├── 1.jpg            (o la versión editada)
        └── original/1_IMG_0006.jpg   (solo si se editó)
```

Columnas del CSV: `sku,nombre,artista,anio,tecnica,tipo,alto_cm,ancho_cm,fondo_cm,precio,fotos,ruta_foto,archivo_original,notas`.
Un CSV existente se abre y se continúa: conserva sus columnas y agrega las que falten.

## Seguridad de los datos

- Nunca sobrescribe fotos ni carpetas existentes.
- El CSV se escribe de forma atómica y se hace un `.bak` antes de la primera escritura de cada sesión.
- Entre discos distintos copia, verifica el hash y recién borra el origen.
- Sin editar, las fotos solo se mueven (no se tocan los píxeles ni el EXIF).

## Estructura del código

- `gatobras/core.py` — lógica sin Qt (CSV, SKU, mover fotos, deshacer, avisos de medidas, configuración).
- `gatobras/ui.py` — ventana, editor de fotos y estilo.
- `tests/test_core.py` — pruebas del núcleo: `python3 -m unittest tests.test_core`.

Notas de diseño y decisiones: ver `CLAUDE.md`. Configuración local en `~/Documents/PolluxData/gatobras_config/`.
