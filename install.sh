#!/bin/sh
# Instalador de gatobras (macOS y Linux). Volver a ejecutarlo actualiza el código y conserva el entorno.
#   curl -fsSL https://raw.githubusercontent.com/seyadog/gatobras/main/install.sh | sh

set -e
DEST="${GATOBRAS_DIR:-$HOME/gatobras}"
REPO="seyadog/gatobras"
OS="$(uname -s)"

# Python: preferir 3.12/3.13 (hay ruedas de PySide6), luego python3
PY=""
for c in python3.12 python3.13 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Falta Python 3. En Mac: brew install python@3.12 (o python.org)"; exit 1; }

echo "→ Descargando gatobras en $DEST"
mkdir -p "$DEST"
TMP="$(mktemp -d)"


curl -fsSL "https://api.github.com/repos/$REPO/tarball/main" | tar xz -C "$TMP"
cp -R "$TMP"/*/. "$DEST"/
rm -rf "$TMP"
chmod +x "$DEST/gatobras.sh"

echo "→ Preparando entorno ($PY)"
[ -d "$DEST/.venv" ] || "$PY" -m venv "$DEST/.venv"
if [ "$OS" = "Darwin" ]; then
  # Qt reciente exige macOS nuevo; el Mac de 2014 llega a macOS 12
  "$DEST/.venv/bin/pip" install -q --upgrade pip
  "$DEST/.venv/bin/pip" install -q "PySide6<6.8"
else
  "$DEST/.venv/bin/pip" install -q -r "$DEST/requirements.txt"
fi

if [ "$OS" = "Darwin" ]; then
  APP="$HOME/Applications/gatobras.app"
  mkdir -p "$APP/Contents/MacOS"
  cat > "$APP/Contents/MacOS/gatobras" <<EOS
#!/bin/sh
exec "$DEST/gatobras.sh"
EOS
  chmod +x "$APP/Contents/MacOS/gatobras"
  cat > "$APP/Contents/Info.plist" <<'EOS'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>gatobras</string>
<key>CFBundleExecutable</key><string>gatobras</string>
<key>CFBundleIdentifier</key><string>local.gatobras</string>
<key>CFBundlePackageType</key><string>APPL</string>
</dict></plist>
EOS
  echo "✔ Listo. Ábrela desde ~/Applications/gatobras.app (o Spotlight: «gatobras»), o con $DEST/gatobras.sh"
else
  echo "✔ Listo. Ejecuta $DEST/gatobras.sh"
fi
