#!/bin/bash
# Attend (marqueurs dans les logs) : fin de la session GPU v4c ET fin des tests Qwen compact ; puis importe Croissant, le teste, et re-prechauffe la v2 de prod.
cd /opt/tinyllm
until grep -q -E "SESSION_OK|Traceback|OutOfMemory" logs/train_v4c.log; do sleep 30; done
until grep -q QWEN_C_DONE logs/c_qwen_tests.log 2>/dev/null; do sleep 30; done
if ! grep -q "MODEL_OK croissant-ha-v4c" logs/train_v4c.log; then echo "croissant non entraine"; echo CROIS_FAILED; exit 1; fi
# espace disque : copie temporaire du gguf, supprimee apres creation
ssh brain.example.lan "cat /var/lib/tinyllm/models/croissant-ha-v4c/q4_k_m.gguf" | ssh localhost "cat > /data/ollama/import/croissant-ha-v4c.gguf"
ssh localhost "cd /data/ollama/import && docker exec ollama sh -c 'ollama show qwen3:1.7b --modelfile' | grep -v '^FROM' | grep -v '^#' > croissant-ha-v4c.params; (echo 'FROM /root/.ollama/import/croissant-ha-v4c.gguf'; cat croissant-ha-v4c.params) > croissant-ha-v4c.Modelfile; docker exec ollama ollama create croissant-ha-v4c -f /root/.ollama/import/croissant-ha-v4c.Modelfile 2>&1 | tail -2; rm -f croissant-ha-v4c.gguf; docker exec ollama ollama list | cut -c1-70"
M="--model croissant-ha-v4c --kind croissant --ctx 2048"
python3 scripts/harness4.py $M --every 2 --out results/c_croissant_none.json > logs/c_croissant_none.log 2>&1
python3 scripts/harness4.py $M --every 2 --hist mix --out results/c_croissant_hist.json > logs/c_croissant_hist.log 2>&1
python3 scripts/harness4.py $M --adv --out results/c_croissant_adv.json > logs/c_croissant_adv.log 2>&1
python3 scripts/harness4.py $M --force-error --every 2 --cats lumiere,volets,scripts,todo,clim,bruit --out results/c_croissant_forceerr.json > logs/c_croissant_forceerr.log 2>&1
# remise en etat de la production : v2 re-chargee et prechauffee avec le prompt exact de la tablette
python3 scripts/warmup_tablet.py qwen3-ha-v2:latest
python3 scripts/warmup_tablet.py qwen3-ha-v2:latest
echo CROIS_DONE
