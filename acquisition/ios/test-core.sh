#!/bin/sh
set -eu
capture_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$capture_root/build/Tests" "$capture_root/build/TestModuleCache"
xcrun swiftc -O -module-cache-path "$capture_root/build/TestModuleCache" "$capture_root/Sources/CaptureCore.swift" "$capture_root/Tests/CoreTests.swift" -o "$capture_root/build/Tests/capture-core-tests"
"$capture_root/build/Tests/capture-core-tests" "$capture_root/build/fixtures" "$@"
