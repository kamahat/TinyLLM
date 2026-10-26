#!/bin/bash
# Rejoue la recette (1 phrase sur 2) avec le TEXTE REELLEMENT transcrit par chaque moteur STT (parole synthetique propre ou bruitee), modele de production qwen3-ha-v5.
cd /opt/tinyllm
export COMPACT_WEB=1; M="--model qwen3-ha-v5 --kind qwen --every 2"
for run in small_clean parakeet_clean kroko_clean base_clean tiny_clean small_noisy parakeet_noisy kroko_noisy; do
  python3 scripts/bench/harness4.py $M --recette data/benchmark_stt_$run.json --out results/e2e_stt_$run.json > logs/e2e_stt_$run.log 2>&1
done
echo E2E_DONE > logs/e2e_done.txt
