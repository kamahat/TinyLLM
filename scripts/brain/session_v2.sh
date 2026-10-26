#!/bin/bash
# Session GPU v2 : libere le GPU de vLLM, test rapide, entrainement, GGUF Q4_K_M, puis RESTAURE vLLM (trap + garde 4 h).
set -e
export TMPDIR=/var/lib/tinyllm/tmp HF_HOME=/var/lib/tinyllm/hf PIP_CACHE_DIR=/var/lib/tinyllm/pipcache
W=/var/lib/tinyllm; NAME=${1:-qwen3-1.7b-ha-v2}
systemd-run --quiet --unit=tinyllm-guard --on-active=4h --description="garde tinyllm : relance vllm" /bin/systemctl start vllm || true
restore() { echo "[$(date +%T)] restauration de vllm"; systemctl stop tinyllm-guard.timer 2>/dev/null || true; systemctl start vllm; }
trap restore EXIT
echo "[$(date +%T)] arret de vllm"; systemctl stop vllm; sleep 10
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
. $W/venv/bin/activate; cd $W/work
python train_v2.py --out $W/models/_smoke2 --n1 40 --n2 20 --accum 4
echo "[$(date +%T)] test rapide OK, entrainement complet"
python train_v2.py --out $W/models/$NAME
LL=/var/lib/llama/llama.cpp
python $LL/convert_hf_to_gguf.py $W/models/$NAME/merged --outfile $W/models/$NAME/f16.gguf --outtype f16
$W/llama-build/bin/llama-quantize $W/models/$NAME/f16.gguf $W/models/$NAME/q4_k_m.gguf Q4_K_M
rm -rf $W/models/_smoke2
ls -la $W/models/$NAME/*.gguf
echo SESSION_OK
