#!/bin/sh
# Retour arriere : proxy v1 (sans web) + qwen3-ha-v4c. Puis prechauffer : python3 warmup_proxy.py (depuis workstation).
set -e
cd /opt/jarvis-proxy
mv app app.web-retiree.$(date +%s)
cp -a app.v1 app
cp docker-compose.v1.yml docker-compose.yml
docker compose up -d --force-recreate
echo "retour arriere fait : proxy v1 + qwen3-ha-v4c"
