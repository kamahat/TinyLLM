#!/bin/bash
# Session GPU v5 (a lancer SUR Brain) : entraine Qwen3-1.7B avec les exemples web (COMPACT_WEB=1), GGUF Q4_K_M. vLLM restaure a la fin (trap + garde 3 h).
set -e
export TMPDIR=/var/lib/tinyllm/tmp HF_HOME=/var/lib/tinyllm/hf COMPACT_WEB=1 TRAIN_FILE=train_v5.json
W=/var/lib/tinyllm; LL=/var/lib/llama/llama.cpp
systemd-run --quiet --unit=tinyllm-guard --on-active=3h --description="garde tinyllm : relance vllm" /bin/systemctl start vllm || true
restore() { echo "[$(date +%T)] restauration de vllm"; systemctl stop tinyllm-guard.timer 2>/dev/null || true; systemctl start vllm; }
trap restore EXIT
echo "[$(date +%T)] arret de vllm"; systemctl stop vllm; sleep 10
. $W/venv/bin/activate; cd $W/work
python train_v4c.py --base Qwen/Qwen3-1.7B --kind qwen --out $W/models/qwen3-1.7b-ha-v5 --n1 2400 --n2 1500 --epochs 1
python $LL/convert_hf_to_gguf.py $W/models/qwen3-1.7b-ha-v5/merged --outfile $W/models/qwen3-1.7b-ha-v5/f16.gguf --outtype f16 >/dev/null 2>&1
$W/llama-build/bin/llama-quantize $W/models/qwen3-1.7b-ha-v5/f16.gguf $W/models/qwen3-1.7b-ha-v5/q4_k_m.gguf Q4_K_M >/dev/null 2>&1
ls -la $W/models/qwen3-1.7b-ha-v5/q4_k_m.gguf; echo SESSION_OK
