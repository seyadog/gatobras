# gatobras

Aplicación de escritorio, **local, en Linux (Wayland)**, para catalogar fotos de obras de arte
con sus datos y dejarlas listas en una carpeta + un CSV. Es un proyecto **aparte** del
e-commerce de Sarapa (`~/Documents/PolluxData/ecommrcesarapa1`); existe para facilitar la
captura de datos que luego alimenta esa tienda.

Responde siempre en español. El usuario escribe rápido y con errores de tipeo: interpreta la
intención, no corrijas ni comentes la ortografía. Prefiere que se documente sin preguntar.

## Estado

**Código escrito y probado en modo `offscreen` el 9-oct-2026** (PySide6 6.12 ya instalado en `.venv`).
Falta probarlo a mano en la ventana real (Wayland). No instales nada ni crees archivos fuera de este directorio sin pedirlo.

### Estructura

- `gatobras/core.py` — lógica sin Qt: CSV atómico + `.bak`, SKU, `safe_move` (nunca sobrescribe;
  copia+hash entre discos), `add_new`, `add_to_existing`, `undo`, `order_dims` (alto/ancho), config.
- `gatobras/ui.py` — ventana PySide6: pestaña «Catalogar» (lista con miniaturas, preview, formulario,
  guardar / agregar a obra existente / deshacer) y pestaña «CSV» (tabla editable con miniaturas
  150 px, abrir con `xdg-open`). Miniaturas y preview en segundo plano con caché (`Loader`).
- `gatobras/__main__.py`, `gatobras.sh` (lanzador: `./gatobras.sh`), `requirements.txt` (PySide6).
- `tests/test_core.py` — 3 pruebas del núcleo (pasan): `python3 -m unittest tests.test_core`.
- `.venv/` — Python 3.14 (PySide6 6.12 tiene rueda abi3, sirve para 3.14).
- Configuración: `~/Documents/PolluxData/gatobras_config/config.json` (último CSV, carpeta, prefijo).

### Pendiente al retomar

Ya verificado (humo offscreen con fotos de prueba): guardar, selección múltiple, deshacer, edición
de celdas en la tabla CSV, CSV viejo de 8 columnas (conserva y añade columnas), `.bak`, y
`load_scaled` con EXIF orientación 6 (sale bien orientada y sin deformar).

1. Ejecutar `./gatobras.sh` con **copias o fotos de prueba** (nunca `ftgoct9/`) y usarla a mano:
   diálogos de archivo nativos en Wayland, aspecto, tamaño de la ventana, comodidad del flujo.
2. Sin probar aún: «Agregar a obra existente…» desde la interfaz (sí probado en `core`), el botón
   «Abrir CSV» (`xdg-open`) y mover entre discos distintos (`safe_move` por copia+hash).
3. Datos de prueba reutilizables: se generaron en el scratchpad de la sesión (se pierden); crear
   unas fotos JPG cualquiera en una carpeta temporal.

### Decisiones tomadas en esta sesión

- **10-oct-2026, editor de fotos (excepción pedida por el usuario a «no tocar los píxeles»):** botón «Girar / recortar
  foto…» (Ctrl+E). La edición se guarda en memoria y se aplica al guardar la obra: `1.jpg` es la versión editada
  (JPG calidad 95, sin EXIF) y el **original intacto** va a `fotos/<SKU>/original/<N>_<nombre>`. Deshacer devuelve el
  original y borra solo la copia editada. Si no se edita, la foto se mueve sin tocar píxeles, como siempre.
- Medidas: alto/ancho nunca se reordenan solos; solo avisa (Enter dos veces para guardar con aviso). Si solo hay una
  de las dos medidas no deja guardar. Nombre/artista opcionales; Enter avanza de campo y en «ancho» guarda.

- **10-oct-2026, diseño de la pestaña «Catalogar» en 3 columnas:** izquierda = carpeta de origen (ruta completa)
  + miniaturas de fotos pendientes; centro = foto actual grande + formulario; derecha = carpeta de destino y CSV
  (ruta completa, nombre, prefijo) + miniaturas de lo ya catalogado. La pestaña «CSV» sigue aparte.
  App instalada en el menú de GNOME (`~/.local/share/applications/gatobras.desktop`, icono `assets/gatobras.svg`).

- **10-oct-2026:** el destino se elige con un diálogo (`DestDialog` en ui.py): carpeta de destino (navegable) +
  nombre del CSV (lista los .csv de esa carpeta o se escribe uno nuevo). El CSV y `fotos/` se crean ahí al
  primer guardado; si el CSV ya existe se abre y continúa. Sin probar con la interfaz (falta PySide6).

- Solo JPG/PNG (sin HEIC). Columna `ruta_foto` incluida (`fotos/<SKU>/N.ext`, relativa al CSV).
- Columnas nuevas del CSV: `sku,nombre,artista,anio,tecnica,tipo,alto_cm,ancho_cm,fondo_cm,precio,
  fotos,ruta_foto,archivo_original,notas`. En un CSV existente se conservan las suyas y las que
  falten se agregan al final; a filas viejas se les rellena `ruta_foto` si la foto existe.
- La tabla de la pestaña CSV es editable y cada edición reescribe el CSV (SKU, `fotos`, `ruta_foto`
  y `archivo_original` son de solo lectura).
- Tras guardar, el formulario conserva alto/ancho/fondo y limpia el resto. `nombre` queda vacío
  si no se escribe (no se inventa «Cuadro CUA-xxx»).
- Alto/ancho se reordenan al terminar de editar ambos campos, según la orientación de la foto;
  aviso si es casi cuadrada y botón ⇄ para intercambiar. En selección múltiple se usan los
  valores del formulario tal cual para todas.
- El deshacer cubre el último guardado completo (incluye lotes de selección múltiple y «agregar a existente»).

## Origen: lo que se hizo a mano el 9-oct-2026

La app automatiza un proceso que ya se hizo manualmente en el repo de la tienda:

- Carpeta de trabajo: `~/Documents/PolluxData/ecommrcesarapa1/ftgoct9/`
  - `catalogo.csv` — 59 filas, `CUA-001` a `CUA-059`
  - `fotos/CUA-001/1.jpg … CUA-059/1.jpg` — fotos JPG originales, sin recomprimir (217 MB)
  - `CLAUDE.md` — reglas del flujo manual
- Documentación completa de esa sesión: `~/Documents/PolluxData/ecommrcesarapa1/docs/catalogo-fotos-ftgoct9.md`
  (decisiones, incidentes, pendientes y tabla de las 59 obras).
- Las fotos de origen estaban en `~/Downloads/wetransfer_img_0009-heic_2026-10-09_2142/fotos_jpg/`
  (ya vacía; se movieron con `mv`). Los HEIC originales siguen en la carpeta de arriba y una foto
  original sigue en el teléfono (Pixel 9a).
- Esas fotos y ese CSV son datos reales del cliente: **no los muevas, borres ni modifiques**
  desde este proyecto. Para probar la app usa copias o fotos de prueba.

Formato del CSV existente (la app debe poder **abrirlo y continuar** desde `CUA-060`):

```
sku,nombre,alto_cm,ancho_cm,fondo_cm,fotos,archivo_original,notas
CUA-001,Cuadro CUA-001,82.6,54.9,,1,IMG_0006.jpg,
```

Medidas en cm, solo números, punto decimal. `fotos` = cuántas fotos hay en la carpeta del SKU.
`archivo_original` = nombre del archivo de origen, para rastrearlo.

## Qué hace la app

1. El usuario elige una **carpeta de fotos** (de cualquier parte del PC) y un **CSV de destino**
   (nuevo o existente). Si es existente, se lee y se continúa.
2. Se muestra la foto en **preview grande**. Debajo, un formulario con campos **todos opcionales**:
   `nombre`, `artista`, `año`, `técnica`, `tipo` (óleo, acuarela, fotografía, objeto…),
   `alto_cm`, `ancho_cm`, `fondo_cm` (grosor del marco), `precio`, `notas`.
   El `sku` se genera solo (ver abajo) y se puede editar. La app rellena `archivo_original` y `fotos`.
3. **Guardar**: mueve la foto a `<carpeta del CSV>/fotos/<SKU>/1.<ext>`, agrega la fila al CSV y
   pasa a la siguiente foto.
4. **SKU automático**: `CUA-001`, `CUA-002`… continuando el último número del CSV. Nunca reutilizar
   un SKU. Prefijo configurable, por defecto `CUA`.
5. **Recordar la última medida**: el formulario conserva alto/ancho de la obra anterior; el
   usuario los cambia solo si difieren (series de obras con el mismo tamaño).
6. **Selección múltiple**: marcar varias fotos y aplicarles los mismos datos de una vez
   (se crean varias filas, un SKU por foto).
7. **Agregar a obra existente**: botón para elegir un SKU ya registrado; la foto va como
   `2.jpg`, `3.jpg`… en su carpeta y suma 1 a la columna `fotos`.
8. **Deshacer el último guardado**: devuelve la foto a su ruta original y borra esa fila del CSV.
9. **Vista del CSV**: tabla con **miniaturas grandes** de cada obra y sus datos, y un botón para
   **abrir el CSV** con el programa por defecto (`xdg-open`).

### Alto y ancho

El usuario escribe las dos medidas **en cualquier orden**. La app decide cuál es alto y cuál es
ancho según la **forma de la obra en la foto** (apoyándose en el tamaño y la orientación EXIF):
foto horizontal → la mayor es el ancho; vertical → la mayor es el alto. Si la obra es casi
cuadrada (medidas casi iguales) o la foto está girada respecto de la obra, **avisar** y dejar que
el usuario las intercambie con un botón. Las medidas son del **objeto físico**, nunca del tamaño
de la foto en píxeles.

## Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Lenguaje / UI | **Python + PySide6 (Qt)**, en un entorno virtual dentro de este directorio |
| Formatos de entrada | Solo **JPG y PNG**. Si hace falta HEIC, se convierte antes con otra herramienta |
| Foto | Se **mueve** (`mv`) al destino. Se conserva el archivo sin tocar los píxeles |
| Destino de fotos | Junto al CSV: `<carpeta del CSV>/fotos/<SKU>/N.<ext>` (rutas relativas) |
| CSV | Uno que el usuario elige; se amplía fila a fila. UTF-8, con comillas si hay comas |
| Deshacer | Solo el último guardado (foto de vuelta + fila borrada) |
| Datos | Todos opcionales; nunca inventar valores (autor, año, precio…) |

## Reglas de seguridad (importan: son fotos y datos irrecuperables del cliente)

- **Nunca sobrescribir** una foto o carpeta que ya exista en el destino.
- Escribir el CSV de forma **atómica** (archivo temporal + renombrar) para no dejarlo a medias.
- Hacer una copia de seguridad del CSV (`.bak`) antes de la primera escritura de cada sesión.
- Mover entre sistemas de archivos distintos = copiar, verificar tamaño/hash y recién borrar el
  origen. Si algo falla, no borrar nada y avisar.
- **No tocar los píxeles**: ni redimensionar, ni recomprimir, ni quitar EXIF. Solo mover y renombrar.
  (La conversión a WebP y la limpieza del GPS son un paso posterior, en el proyecto de la tienda.)
- No hacer commits ni `git add` salvo que el usuario lo pida.
- Preservar columnas desconocidas del CSV al abrirlo; añadir las que falten sin romper las filas.

## Notas técnicas

- Máquina: Fedora, Wayland, Python **3.14**. Antes de empezar, **verificar que PySide6 tenga
  ruedas para 3.14**; si no, crear el venv con un Python más antiguo (3.12/3.13).
- Las fotos son grandes (hasta 5712×4284 px, 3-8 MB). Cargar el preview **reducido** y las
  miniaturas en segundo plano con caché, para que la interfaz no se congele.
- Diálogos de archivo: usar los nativos de Qt (portal XDG en Wayland).
- Mantener la aplicación pequeña y sin dependencias innecesarias.

## Dudas resueltas (9-oct-2026)

- HEIC: **no**, solo JPG/PNG.
- Paquete/comando `gatobras`; configuración en `~/Documents/PolluxData/gatobras_config/`.
- Columna `ruta_foto`: **sí**, y el CSV se puede editar desde la app (pestaña CSV).

## Siguiente paso fuera de este proyecto

Un script en el repo de la tienda lee el CSV: convierte las fotos a WebP (1600 px y miniatura
400 px, **sin EXIF/GPS**), las sube al bucket `sarapa-tienda-obras` de OCI y crea los productos
en Medusa con sus medidas. No es parte de gatobras.
