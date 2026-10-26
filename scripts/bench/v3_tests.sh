#!/bin/bash
cd /opt/tinyllm
T="--real data/ha_tablet_prompt.json"
python3 scripts/harness2.py --model qwen3-ha-v3 $T --hist mix --every 2 --out results/tablet_v3_hist.json > logs/tablet_v3_hist.log 2>&1
python3 scripts/harness2.py --model qwen3-ha-v3 $T --every 2 --out results/tablet_v3.json > logs/tablet_v3.log 2>&1
python3 scripts/harness2.py --model qwen3-ha-v3 $T --adv --out results/tablet_v3_adv.json > logs/tablet_v3_adv.log 2>&1
python3 scripts/harness2.py --model qwen3-ha-v3 $T --force-error --every 2 --cats lumiere,volets,scripts,todo,clim,bruit --out results/tablet_v3_forceerr.json > logs/tablet_v3_forceerr.log 2>&1
echo V3_TESTS_DONE
