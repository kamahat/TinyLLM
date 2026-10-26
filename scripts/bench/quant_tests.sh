#!/bin/bash
# Recette complete + banc web pour une variante quantifiee, sur l instance Ollama de TEST (port 11435) : la production (11434) n est pas touchee. Usage : q2_tests.sh NOM_MODELE ETIQUETTE
cd /opt/tinyllm
MODEL=$1; TAG=$2; export COMPACT_WEB=1 OLLAMA_URL=http://localhost:11435
M="--model $MODEL --kind ${KIND:-qwen} --host http://localhost:11435"
python3 scripts/harness5_web.py $MODEL > logs/q2_${TAG}_web.log 2>&1
python3 scripts/harness4.py $M --every 2 --out results/c_${TAG}_none.json > logs/c_${TAG}_none.log 2>&1
python3 scripts/harness4.py $M --every 2 --hist mix --out results/c_${TAG}_hist.json > logs/c_${TAG}_hist.log 2>&1
python3 scripts/harness4.py $M --adv --out results/c_${TAG}_adv.json > logs/c_${TAG}_adv.log 2>&1
python3 scripts/harness4.py $M --force-error --every 2 --cats lumiere,volets,scripts,todo,clim,bruit --out results/c_${TAG}_forceerr.json > logs/c_${TAG}_forceerr.log 2>&1
echo DONE > logs/q2_${TAG}_done.txt
