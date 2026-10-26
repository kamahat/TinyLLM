#!/bin/bash
# Attend que le GPU de Brain ne serve plus aux modes creation/analyse/image (usage de Alex), 2 controles de suite, puis lance la session v3.
B=brain.example.lan; ok=0
while true; do
  act=$(ssh -o BatchMode=yes $B "systemctl list-units --type=service --state=active --no-pager --plain --no-legend | awk '{print \$1}' | grep -E '^(llama-|comfyui)' | tr '\n' ' '")
  if [ -z "$act" ]; then ok=$((ok+1)); else ok=0; echo "[$(date +%T)] GPU occupe par : $act"; fi
  [ $ok -ge 2 ] && break
  sleep 45
done
echo "[$(date +%T)] GPU libre : lancement de la session v3"
ssh $B bash /var/lib/tinyllm/session_v3.sh qwen3-1.7b-ha-v3
