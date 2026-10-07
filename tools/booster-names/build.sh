#!/usr/bin/env bash
# Builds the booster names tool: a small dumper added to FileDiver, for Windows, plus a
# double-click runner, packed as dist/booster-names-tool.zip. Run by
# .github/workflows/booster-names-tool.yml; works locally too (Go 1.24+, git, zip).
#
#   tools/booster-names/build.sh              # pinned FileDiver commit
#   FILEDIVER_REF=master tools/booster-names/build.sh
#   MIRRORS=1 tools/booster-names/build.sh    # no proxy.golang.org: golang.org/x from GitHub mirrors
#
# FileDiver (https://github.com/xypwn/filediver, BSD-3-Clause, by xypwn and contributors) is
# used unchanged; dumper/main.go is added to its cmd/tools/components/ and built with it.
# It reads the game install (read-only) and prints what the files say about boosters.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REF="${FILEDIVER_REF:-6d66a9c}"          # FileDiver master, 2026-09-30
WORK="$(mktemp -d)"
OUT="${OUT:-$HERE/dist}"
trap 'rm -rf "$WORK"' EXIT

git clone -q https://github.com/xypwn/filediver "$WORK/filediver"
git -C "$WORK/filediver" checkout -q "$REF"
COMMIT="$(git -C "$WORK/filediver" rev-parse --short HEAD)"
cd "$WORK/filediver"

export GOOS="${GOOS:-windows}" GOARCH=amd64 CGO_ENABLED=0
if [ "${MIRRORS:-0}" = "1" ]; then
    # Build hosts without proxy.golang.org: fetch golang.org/x/* from github.com/golang/*
    # at the versions go.sum pins, and let a local Go toolchain build it.
    for m in sys term text image mod sync tools exp; do
        ver="$(awk -v p="golang.org/x/$m" '$1==p && $2 !~ /go.mod$/ {print $2; exit}' go.sum)"
        [ -n "$ver" ] || continue
        rev="${ver##*-}"; case "$ver" in v0.0.0-*) ;; *) rev="$ver" ;; esac
        git clone -q https://github.com/golang/$m "$WORK/x/$m"
        git -C "$WORK/x/$m" checkout -q "$rev"
        sed -i -E 's/^go 1\.(2[5-9])(\.[0-9]+)?$/go 1.24/; /^toolchain/d' "$WORK/x/$m/go.mod"
        echo "replace golang.org/x/$m => $WORK/x/$m" >> go.mod
    done
    sed -i -E 's/^go 1\.(2[5-9])(\.[0-9]+)?$/go 1.24/; /^toolchain/d' go.mod
    export GOTOOLCHAIN=local GOPROXY=direct GOSUMDB=off GOFLAGS=-mod=mod
fi

mkdir -p cmd/tools/components/booster-dumper
cp "$HERE/dumper/main.go" cmd/tools/components/booster-dumper/main.go

mkdir -p "$WORK/pkg" "$OUT"
go build -trimpath -o "$WORK/pkg/booster-dumper.exe" ./cmd/tools/components/booster-dumper
cp LICENSE "$WORK/pkg/LICENSE-filediver.txt"
cp "$HERE/Run-me.bat" "$WORK/pkg/"
sed "s/@COMMIT@/$COMMIT/" "$HERE/README.txt" > "$WORK/pkg/README.txt"
(cd "$WORK/pkg" && rm -f "$OUT/booster-names-tool.zip" && zip -q -9 "$OUT/booster-names-tool.zip" ./*)
sha256sum "$WORK/pkg/booster-dumper.exe" | tee "$OUT/booster-dumper.exe.sha256"
echo "built $OUT/booster-names-tool.zip from FileDiver $COMMIT"
