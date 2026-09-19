#!/bin/sh
set -eu
capture_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
xcodebuild -project "$capture_root/EchoSightCapture.xcodeproj" -scheme EchoSightCapture -destination generic/platform=iOS -derivedDataPath "$capture_root/build/DerivedData" -configuration Release -sdk iphoneos CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY= SYMROOT="$capture_root/build/Products" OBJROOT="$capture_root/build/Intermediates" CLANG_MODULE_CACHE_PATH="$capture_root/build/ModuleCache" MODULE_CACHE_DIR="$capture_root/build/ModuleCache" SDK_STAT_CACHE_DIR="$capture_root/build/SDKStatCaches" build
