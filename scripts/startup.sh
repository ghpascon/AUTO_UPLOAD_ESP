#!/usr/bin/env bash
set -euo pipefail

# Cria entrada de autostart em ambientes Linux compatíveis com XDG.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
DESKTOP_FILE="${AUTOSTART_DIR}/smartx.desktop"

if [[ -x "${SCRIPT_DIR}/main" ]]; then
    EXEC_CMD="${SCRIPT_DIR}/main"
elif [[ -x "${SCRIPT_DIR}/main.exe" ]]; then
    EXEC_CMD="${SCRIPT_DIR}/main.exe"
elif [[ -f "${SCRIPT_DIR}/main.exe" ]] && command -v wine >/dev/null 2>&1; then
    EXEC_CMD="wine ${SCRIPT_DIR}/main.exe"
else
    echo "main ou main.exe nao encontrado em ${SCRIPT_DIR}"
    echo "Coloque o executavel na pasta scripts/ ou ajuste startup.sh."
    exit 1
fi

mkdir -p "${AUTOSTART_DIR}"

cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=Smartx
Exec=${EXEC_CMD}
Path=${SCRIPT_DIR}
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Autostart criado em: ${DESKTOP_FILE}"
