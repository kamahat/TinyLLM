#!/bin/bash
# Session GPU : libere le GPU de vLLM, entraine, convertit en GGUF, puis RESTAURE vLLM (trap + garde 4 h).
set -e
export TMPDIR=/var/lib/tinyllm/tmp HF_HOME=/var/lib/tinyllm/hf PIP_CACHE_DIR=/var/lib/tinyllm/pipcache
W=/var/lib/tinyllm; MODE=${1:-full}; NAME=${2:-qwen3-1.7b-ha-v1}
systemd-run --quiet --unit=tinyllm-guard --on-active=4h --description="garde tinyllm : relance vllm" /bin/systemctl start vllm || true
restore() { echo "[$(date +%T)] restauration de vllm"; systemctl stop tinyllm-guard.timer 2>/dev/null || true; systemctl start vllm; }
trap restore EXIT
echo "[$(date +%T)] arret de vllm"; systemctl stop vllm; sleep 10
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
. $W/venv/bin/activate; cd $W/work
if [ "$MODE" = smoke ]; then
  python train_lora.py --out $W/models/_smoke --epochs 0.4 --limit 120 --accum 4
  exit 0
fi
python train_lora.py --out $W/models/$NAME --epochs 2
LL=/var/lib/llama/llama.cpp
python $LL/convert_hf_to_gguf.py $W/models/$NAME/merged --outfile $W/models/$NAME/f16.gguf --outtype f16
if [ ! -x $W/llama-build/bin/llama-quantize ]; then
  cmake -S $LL -B $W/llama-build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release >/dev/null && cmake --build $W/llama-build --target llama-quantize -j8 2>&1 | tail -2
fi
$W/llama-build/bin/llama-quantize $W/models/$NAME/f16.gguf $W/models/$NAME/q4_k_m.gguf Q4_K_M
ls -la $W/models/$NAME/*.gguf
echo SESSION_OK
