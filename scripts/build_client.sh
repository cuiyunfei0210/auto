#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install --upgrade pyinstaller
python3 -m PyInstaller --noconfirm random_org_gui.spec
mkdir -p delivery
cp -f packaging/客户使用说明.txt delivery/
if [[ -f dist/RandomNumberGenerator.exe ]]; then
  cp -f dist/RandomNumberGenerator.exe delivery/
else
  cp -f dist/RandomNumberGenerator delivery/
fi
echo "Client files are in: $(pwd)/delivery"
