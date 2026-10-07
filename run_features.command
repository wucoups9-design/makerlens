#!/bin/sh
set -eu
MAKERLENS_SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$MAKERLENS_SCRIPT_DIR"
echo '打开 http://127.0.0.1:8766/ 。按 Control+C 关闭本机网站。'
MAKERLENS_PYTHON="${MAKERLENS_PYTHON:-/Users/gao/Documents/makerlens-yolo/bin/python}"
MAKERLENS_MODELS="${MAKERLENS_MODELS:-$MAKERLENS_SCRIPT_DIR/../MakerLens_interview_demo_20260926/models}"
if [ ! -x "$MAKERLENS_PYTHON" ]; then
  echo '找不到模型运行环境，请设置 MAKERLENS_PYTHON。'
  exit 1
fi
MAKERLENS_GLOVES="${MAKERLENS_GLOVES:-/Users/gao/Documents/MakerLens-training/gloves-v4-reviewed-20261005/weights/best.pt}"
if [ ! -f "$MAKERLENS_GLOVES" ]; then
  echo '找不到新手套模型，请设置 MAKERLENS_GLOVES 或恢复旧模型路径。'
  exit 1
fi
exec "$MAKERLENS_PYTHON" dev_server.py --port 8766 --sketch-ai --ppe-models "$MAKERLENS_MODELS" --gloves-model "$MAKERLENS_GLOVES"
