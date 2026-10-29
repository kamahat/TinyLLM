#!/bin/bash
# Session GPU Gemma 3 1B (a lancer SUR Brain) : meme recette que la v5 Qwen (train_v6.json, LoRA r=32, 1 epoque), format gemma, GGUF Q4_K_M. vLLM restaure a la fin (trap + garde 3 h).
set -e
export TMPDIR=/var/lib/tinyllm/tmp HF_HOME=/var/lib/tinyllm/hf COMPACT_WEB=1 TRAIN_FILE=train_v6.json
W=/var/lib/tinyllm; LL=/var/lib/llama/llama.cpp; OUT=$W/models/gemma3-1b-ha-v6
systemd-run --quiet --unit=ha-llm-eval-guard --on-active=3h --description="garde ha-llm-eval : relance vllm" /bin/systemctl start vllm || true
restore() { echo "[$(date +%T)] restauration de vllm"; systemctl stop ha-llm-eval-guard.timer 2>/dev/null || true; systemctl start vllm; }
trap restore EXIT
echo "[$(date +%T)] arret de vllm"; systemctl stop vllm; sleep 10
. $W/venv/bin/activate; cd $W/work
python train_v4c.py --base unsloth/gemma-3-1b-it --kind gemma --out $OUT --n1 2400 --n2 1500 --epochs 1
B=$(ls -d $W/hf/hub/models--unsloth--gemma-3-1b-it/snapshots/*); for f in tokenizer.json tokenizer.model tokenizer_config.json special_tokens_map.json added_tokens.json; do cp $B/$f $OUT/merged/$f; done   # OBLIGATOIRE : sinon le GGUF perd les jetons speciaux
echo "[$(date +%T)] conversion GGUF"
python $LL/convert_hf_to_gguf.py $OUT/merged --outfile $OUT/f16.gguf --outtype f16 > $W/convert_gemma_v6.log 2>&1
$W/llama-build/bin/llama-quantize $OUT/f16.gguf $OUT/q4_k_m.gguf Q4_K_M > $W/quantize_gemma_v6.log 2>&1
ls -la $OUT/q4_k_m.gguf; echo SESSION_OK
