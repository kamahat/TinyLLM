#!/bin/bash
# Session GPU v4d : Croissant reentraine avec la tokenisation EXACTE de llama.cpp (serveur /tokenize), puis GGUF Q4_K_M. Restaure vLLM a la fin.
set -e
export TMPDIR=/var/lib/tinyllm/tmp HF_HOME=/var/lib/tinyllm/hf
W=/var/lib/tinyllm; LL=/var/lib/llama/llama.cpp
systemd-run --quiet --unit=tinyllm-guard --on-active=3h --description="garde tinyllm : relance vllm" /bin/systemctl start vllm || true
cleanup() { kill $SPID 2>/dev/null || true; echo "[$(date +%T)] restauration de vllm"; systemctl stop tinyllm-guard.timer 2>/dev/null || true; systemctl start vllm; }
trap cleanup EXIT
echo "[$(date +%T)] arret de vllm"; systemctl stop vllm; sleep 10
$LL/build/bin/llama-server -m $W/models/croissant-ha-v4c/q4_k_m.gguf -ngl 0 -c 512 --port 8099 --host 127.0.0.1 >/dev/null 2>&1 & SPID=$!
for i in $(seq 1 60); do curl -s -m 2 http://127.0.0.1:8099/health >/dev/null && break; sleep 2; done
. $W/venv/bin/activate; cd $W/work
python train_v4c.py --base croissantllm/CroissantLLMChat-v0.1 --kind croissant --out $W/models/croissant-ha-v4d --n1 2200 --n2 1300 --epochs 1.5 --tok-server http://127.0.0.1:8099
kill $SPID 2>/dev/null || true
python $LL/convert_hf_to_gguf.py $W/models/croissant-ha-v4d/merged --outfile $W/models/croissant-ha-v4d/f16.gguf --outtype f16 >/dev/null 2>&1
$W/llama-build/bin/llama-quantize $W/models/croissant-ha-v4d/f16.gguf $W/models/croissant-ha-v4d/q4_k_m.gguf Q4_K_M >/dev/null 2>&1
ls -la $W/models/croissant-ha-v4d/q4_k_m.gguf; echo SESSION_OK
