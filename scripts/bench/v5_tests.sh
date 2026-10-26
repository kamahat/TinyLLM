#!/bin/bash
cd /opt/tinyllm
python3 scripts/harness5_web.py qwen3-ha-v5 > logs/v5_web.log 2>&1
export COMPACT_WEB=1; M="--model qwen3-ha-v5 --kind qwen"
python3 scripts/harness4.py $M --every 2 --out results/c_qwen5_none.json > logs/c_qwen5_none.log 2>&1
python3 scripts/harness4.py $M --every 2 --hist mix --out results/c_qwen5_hist.json > logs/c_qwen5_hist.log 2>&1
python3 scripts/harness4.py $M --adv --out results/c_qwen5_adv.json > logs/c_qwen5_adv.log 2>&1
python3 scripts/harness4.py $M --force-error --every 2 --cats lumiere,volets,scripts,todo,clim,bruit --out results/c_qwen5_forceerr.json > logs/c_qwen5_forceerr.log 2>&1
echo V5_DONE
