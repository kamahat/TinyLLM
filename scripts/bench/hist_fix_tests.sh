#!/bin/bash
cd /opt/tinyllm
M="--model qwen3-ha-v4c --kind qwen"
python3 scripts/harness4.py $M --every 2 --hist mix --out results/c_qwen_hist_fix.json > logs/c_qwen_hist_fix.log 2>&1
python3 scripts/harness4.py $M --every 2 --out results/c_qwen_none_fix.json > logs/c_qwen_none_fix.log 2>&1
echo FIX_DONE
