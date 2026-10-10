# gatobras

Aplicación de escritorio, **local, en Linux (Wayland)**, para catalogar fotos de obras de arte
con sus datos y dejarlas listas en una carpeta + un CSV. Es un proyecto **aparte** del
e-commerce de Sarapa (`~/Documents/PolluxData/ecommrcesarapa1`); existe para facilitar la
captura de datos que luego alimenta esa tienda.

Responde siempre en español. El usuario escribe rápido y con errores de tipeo: interpreta la
intención, no corrijas ni comentes la ortografía. Prefiere que se documente sin preguntar.

## Estado

**Actualizado el 10-oct-2026.** App funcional y probada en modo `offscreen` (PySide6 6.12 instalado en `.venv`,
Python 3.14). Instalada en el menú de GNOME. Repo privado: https://github.com/seyadog/gatobras (rama `main`).
Falta usarla a mano con fotos reales. No instales nada ni crees archivos fuera de este directorio sin pedirlo
(el lanzador e icono en `~/.local/share` se crearon porque el usuario lo pidió).

Los cambios se ven al cerrar y volver a abrir la app (se ejecuta desde el código fuente, no hay compilación).
Al cambiar algo, comprobar que arranca sin errores antes de avisar.

### Estructura

- `gatobras/core.py` — lógica sin Qt: CSV atómico + `.bak`, SKU, `safe_move` (nunca sobrescribe; copia+hash
  entre discos), `add_new` / `add_to_existing` (con `processed=` para fotos editadas), `undo`, `check_dims`
  (solo avisos de medidas; `order_dims` queda sin uso en la UI), configuración.
- `gatobras/ui.py` — PySide6: estilo oscuro estilo GNOME (`STYLE`), `MainWindow` (pestaña «Catalogar» en 3
  columnas y pestaña «CSV» con tabla editable), `DestDialog` (carpeta de destino + nombre del CSV),
  `EditorDialog`/`CropView` (girar y recortar), `Loader` (miniaturas en segundo plano con caché).
- `gatobras/__main__.py`, `gatobras.sh` (lanzador), `requirements.txt` (PySide6), `assets/gatobras.svg` (gato negro).
- `tests/test_core.py` — pruebas del núcleo (pasan): `.venv/bin/python -m unittest tests.test_core`.
- `README.md` — uso y estructura para humanos.
- Configuración: `~/Documents/PolluxData/gatobras_config/config.json` (último CSV, carpeta, prefijo).
- Instalación en GNOME: `~/.local/share/applications/gatobras.desktop` + icono en
  `~/.local/share/icons/hicolor/scalable/apps/gatobras.svg`.

### Interfaz y flujo (decidido el 10-oct-2026)

- **Pestaña «Catalogar», 3 columnas:** izquierda = carpeta de origen (ruta completa) + miniaturas de pendientes;
  centro = foto actual grande + botón «Girar / recortar» + formulario; derecha = destino (ruta, nombre del CSV,
  prefijo) + miniaturas de lo ya catalogado, **la última guardada arriba**.
- **Destino:** un diálogo con carpeta navegable + nombre del CSV (lista los `.csv` de esa carpeta o se escribe uno
  nuevo). El CSV y `fotos/` se crean al primer guardado; si el CSV ya existe se abre y continúa.
- **Flujo con teclado:** nombre ⏎ artista ⏎ alto ⏎ ancho ⏎ → guarda y pasa a la siguiente foto (cursor vuelve a
  «Nombre»). SKU, año, técnica, tipo, fondo y notas están en «Otros datos (opcional)», fuera del flujo de Enter.
  **Precio se quitó del formulario** (la columna sigue en el CSV, vacía).
- **Todo es opcional** (nombre, artista…), salvo: si hay solo una de las dos medidas no deja guardar (hay que poner
  las dos o ninguna; las obras sin medidas se completan después).
- **Alto/ancho nunca se reordenan solos.** `check_dims` solo avisa si la forma de la foto contradice las medidas
  («Ojo: la foto es vertical pero…»); con aviso, el primer Enter en «ancho» no guarda y el segundo sí. Casi
  cuadradas: sin aviso. Botón ⇄ para intercambiar. El botón «Guardar y siguiente» guarda directo.
- **Editor de fotos (excepción pedida por el usuario a «no tocar los píxeles»):** Ctrl+E. Girar ±90° y recortar
  con rectángulo (mover/estirar). La edición vive en memoria (`self.edits`) y se aplica al guardar: `1.jpg` es la
  versión editada (JPG calidad 95, sin EXIF; PNG sin pérdida) y el **original intacto** va a
  `fotos/<SKU>/original/<N>_<nombre>`. Deshacer devuelve el original y borra solo la copia editada. Sin edición,
  la foto solo se mueve. Las fotos editadas se marcan con ✎ en la lista; el preview y el aviso de medidas usan la
  foto ya editada.
- Look: fondo oscuro `#242424`, tarjetas `#303030` redondeadas, acento azul `#3584e4`, estilo Fusion.

### Decisiones de datos (9-oct-2026, siguen vigentes)

- Solo JPG/PNG (sin HEIC). Columna `ruta_foto` (`fotos/<SKU>/N.ext`, relativa al CSV).
- Columnas del CSV: `sku,nombre,artista,anio,tecnica,tipo,alto_cm,ancho_cm,fondo_cm,precio,fotos,ruta_foto,
  archivo_original,notas`. En un CSV existente se conservan las suyas y las que falten se agregan al final;
  a filas viejas se les rellena `ruta_foto` si la foto existe.
- La tabla de la pestaña CSV es editable y cada edición reescribe el CSV (SKU, `fotos`, `ruta_foto` y
  `archivo_original` son de solo lectura).
- Tras guardar, el formulario conserva alto/ancho/fondo y limpia el resto. `nombre` queda vacío si no se escribe.
- En selección múltiple se usan los valores del formulario tal cual para todas (sin confirmación por aviso).
- El deshacer cubre el último guardado completo (lotes de selección múltiple, «agregar a existente» y editadas).

### Pendiente (retomar aquí)

Verificado offscreen con fotos de prueba: guardar, Enter-flujo, aviso de medidas y doble Enter, selección múltiple,
deshacer, edición de celdas del CSV, CSV viejo de 8 columnas, `.bak`, `load_scaled` con EXIF 6, editor
(girar+recortar+guardar+deshacer), orden de «Ya en el destino».

1. **Usarla a mano** con copias/fotos de prueba (nunca `ftgoct9/`): diálogos nativos en Wayland, tamaño de ventana,
   comodidad del flujo, el aspecto real (las capturas fueron offscreen). Probar con una foto vertical real del Pixel.
2. Sin probar aún en la ventana real: «Agregar a obra existente…», el botón «Abrir CSV» (`xdg-open`), mover entre
   discos distintos, y el editor con ratón real (se probó simulando eventos).
3. Ideas propuestas y NO hechas (el usuario eligió dejarlas para después): enderezar con ángulo fino (±10°),
   brillo/contraste, zoom en la foto grande, buscar/filtrar en la pestaña CSV, aviso de fotos duplicadas,
   aviso/lista de obras sin medidas, ordenar pendientes por fecha o nombre. Recomendadas primero: obras sin
   medidas, zoom, enderezar.
4. Los datos de prueba se generan en el scratchpad (se pierden): crear unas JPG cualquiera en una carpeta temporal.
5. Si `.venv` falta: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (PySide6 pesa mucho).

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

El usuario escribe alto y ancho **en el orden que quiere** y la app los respeta (no los reordena). Solo **avisa**
cuando la forma de la obra en la foto (ya con EXIF y edición aplicados) contradice las medidas; el usuario decide
(botón ⇄ o seguir con un segundo Enter). Las medidas son del **objeto físico**, nunca del tamaño de la foto en píxeles.

## Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Lenguaje / UI | **Python + PySide6 (Qt)**, en un entorno virtual dentro de este directorio |
| Formatos de entrada | Solo **JPG y PNG**. Si hace falta HEIC, se convierte antes con otra herramienta |
| Foto | Se **mueve** al destino sin tocar los píxeles; si el usuario la edita (girar/recortar), `1.jpg` es la editada y el original va a `original/` |
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
- **No tocar los píxeles** salvo que el usuario edite la foto a propósito (girar/recortar; el original queda intacto en `original/`): ni redimensionar, ni recomprimir, ni quitar EXIF. Solo mover y renombrar.
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
