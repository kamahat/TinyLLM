#!/bin/bash
# usage: import_ollama.sh <gguf sur Brain> <nom du modele ollama>
# Copie le GGUF Brain -> volume Ollama du docker (/data/ollama) et cree le modele, sans toucher aux modeles existants.
set -e
SRC=$1; NAME=$2; DK=localhost; VOL=/data/ollama/import
ssh -o BatchMode=yes brain.example.lan "cat $SRC" | ssh -o BatchMode=yes $DK "mkdir -p $VOL && cat > $VOL/$NAME.gguf"
ssh -o BatchMode=yes $DK "docker exec ollama sh -c 'ollama show qwen3:1.7b --modelfile' | grep -v '^FROM' | grep -v '^#' > $VOL/$NAME.params; (echo 'FROM /root/.ollama/import/$NAME.gguf'; cat $VOL/$NAME.params) > $VOL/$NAME.Modelfile; docker exec ollama ollama create $NAME -f /root/.ollama/import/$NAME.Modelfile 2>&1 | tail -2; rm -f $VOL/$NAME.gguf; docker exec ollama ollama list"
