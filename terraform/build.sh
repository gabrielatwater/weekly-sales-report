#!/usr/bin/env bash
# Builds the Lambda package: our Python files + the groq library.
#
# Lambda runs Linux (x86_64) with Python 3.12, so we ask pip for libraries
# built for THAT platform, whatever computer this script runs on.
#
# Usage (from the terraform folder):  bash build.sh
set -euo pipefail
cd "$(dirname "$0")"

rm -rf build/package
mkdir -p build/package

pip3 install groq \
  --target build/package \
  --platform manylinux2014_x86_64 \
  --python-version 3.12 \
  --implementation cp \
  --only-binary=:all: \
  --quiet

cp ../lambda_function.py ../report.py ../summary.py ../ai_summary.py build/package/

echo "Built build/package ($(du -sh build/package | cut -f1))"
