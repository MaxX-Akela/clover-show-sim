#!/bin/bash
set -euo pipefail

VERSION="${1:?версия PX4, например 1.13.3}"
OUT="$(realpath -m "${2:?каталог результата}")"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

git clone --recursive --depth 1 --branch "v${VERSION}" https://github.com/PX4/PX4-Autopilot.git "$WORK/px4"
cd "$WORK/px4"
make px4_sitl_default

BUILD=build/px4_sitl_default
[ -x "$BUILD/bin/px4" ] || { echo "нет $BUILD/bin/px4"; exit 1; }
[ -f "$BUILD/etc/init.d-posix/rcS" ] || { echo "нет $BUILD/etc/init.d-posix/rcS"; exit 1; }

mkdir -p "$OUT" "$WORK/pkg"
cp -rL "$BUILD/bin" "$BUILD/etc" "$WORK/pkg/"
echo "$VERSION" > "$WORK/pkg/VERSION"
tar -C "$WORK/pkg" -czf "$OUT/px4_sitl_default-${VERSION}.tar.gz" bin etc VERSION
echo "готово: $OUT/px4_sitl_default-${VERSION}.tar.gz"
