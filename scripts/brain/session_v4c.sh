#!/bin/bash
# Session GPU v4c : Qwen3-1.7B puis CroissantLLM, format COMPACT. Libere le GPU de vLLM, restaure a la fin (trap + garde 5 h).
set -e
export TMPDIR=/var/lib/tinyllm/tmp HF_HOME=/var/lib/tinyllm/hf PIP_CACHE_DIR=/var/lib/tinyllm/pipcache
W=/var/lib/tinyllm; LL=/var/lib/llama/llama.cpp
systemd-run --quiet --unit=tinyllm-guard --on-active=5h --description="garde tinyllm : relance vllm" /bin/systemctl start vllm || true
restore() { echo "[$(date +%T)] restauration de vllm"; systemctl stop tinyllm-guard.timer 2>/dev/null || true; systemctl start vllm; }
trap restore EXIT
echo "[$(date +%T)] arret de vllm"; systemctl stop vllm; sleep 10
. $W/venv/bin/activate; cd $W/work
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
one() {   # nom, base, kind, epochs
  python train_v4c.py --base $2 --kind $3 --out $W/models/$1 --n1 2200 --n2 1300 --epochs $4
  python $LL/convert_hf_to_gguf.py $W/models/$1/merged --outfile $W/models/$1/f16.gguf --outtype f16 >/dev/null 2>&1
  $W/llama-build/bin/llama-quantize $W/models/$1/f16.gguf $W/models/$1/q4_k_m.gguf Q4_K_M >/dev/null 2>&1
  ls -la $W/models/$1/q4_k_m.gguf; echo "MODEL_OK $1"
}
one qwen3-1.7b-ha-v4c Qwen/Qwen3-1.7B qwen 1
one croissant-ha-v4c croissantllm/CroissantLLMChat-v0.1 croissant 1.5
echo SESSION_OK
