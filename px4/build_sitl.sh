#!/bin/bash
set -euo pipefail

VERSION="${1:?версия PX4, например 1.13.3 или 1.8.2-clever.10}"
OUT="$(realpath -m "${2:?каталог результата}")"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

case "$VERSION" in
    1.8.*-clever*) LEGACY=1; REPO=https://github.com/CopterExpress/Firmware.git; BUILD_DIR=posix_sitl_default ;;
    *) LEGACY=0; REPO=https://github.com/PX4/PX4-Autopilot.git; BUILD_DIR=px4_sitl_default ;;
esac

git clone --recursive --depth 1 --branch "v${VERSION}" "$REPO" "$WORK/px4"
cd "$WORK/px4"
make "$BUILD_DIR"

BUILD="build/$BUILD_DIR"
mkdir -p "$OUT" "$WORK/pkg"
if [ "$LEGACY" = 1 ]; then
    [ -x "$BUILD/px4" ] || { echo "нет $BUILD/px4"; exit 1; }
    [ -f ROMFS/px4fmu_common/mixers/quad_w.main.mix ] || { echo "нет ROMFS/px4fmu_common/mixers/quad_w.main.mix"; exit 1; }
    mkdir -p "$WORK/pkg/bin" "$WORK/pkg/ROMFS/px4fmu_common"
    cp "$BUILD/px4" "$WORK/pkg/bin/px4"
    cp -rL ROMFS/px4fmu_common/mixers "$WORK/pkg/ROMFS/px4fmu_common/"
    echo "$VERSION" > "$WORK/pkg/VERSION"
    tar -C "$WORK/pkg" -czf "$OUT/px4_sitl_default-${VERSION}.tar.gz" bin ROMFS VERSION
else
    [ -x "$BUILD/bin/px4" ] || { echo "нет $BUILD/bin/px4"; exit 1; }
    [ -f "$BUILD/etc/init.d-posix/rcS" ] || { echo "нет $BUILD/etc/init.d-posix/rcS"; exit 1; }
    cp -rL "$BUILD/bin" "$BUILD/etc" "$WORK/pkg/"
    echo "$VERSION" > "$WORK/pkg/VERSION"
    tar -C "$WORK/pkg" -czf "$OUT/px4_sitl_default-${VERSION}.tar.gz" bin etc VERSION
fi
echo "готово: $OUT/px4_sitl_default-${VERSION}.tar.gz"
