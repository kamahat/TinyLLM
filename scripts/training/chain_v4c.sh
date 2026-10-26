#!/bin/bash
# Attend la fin de la session v3 (marqueur dans son log), puis lance la session v4c.
until grep -q -E "SESSION_OK|Traceback|OutOfMemory" /opt/tinyllm/logs/train_v3b.log; do sleep 30; done
if ! grep -q SESSION_OK /opt/tinyllm/logs/train_v3b.log; then echo "v3 en echec : v4c non lancee"; exit 1; fi
echo "[$(date +%T)] v3 terminee, lancement de v4c"; sleep 20
ssh brain.example.lan bash /var/lib/tinyllm/session_v4c.sh
