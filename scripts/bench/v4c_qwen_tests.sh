#!/bin/bash
cd /opt/tinyllm
M="--model qwen3-ha-v4c --kind qwen"
python3 scripts/harness4.py $M --every 2 --out results/c_qwen_none.json > logs/c_qwen_none.log 2>&1
python3 scripts/harness4.py $M --every 2 --hist mix --out results/c_qwen_hist.json > logs/c_qwen_hist.log 2>&1
python3 scripts/harness4.py $M --adv --out results/c_qwen_adv.json > logs/c_qwen_adv.log 2>&1
python3 scripts/harness4.py $M --force-error --every 2 --cats lumiere,volets,scripts,todo,clim,bruit --out results/c_qwen_forceerr.json > logs/c_qwen_forceerr.log 2>&1
echo QWEN_C_DONE
