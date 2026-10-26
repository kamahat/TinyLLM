H=localhost
echo "== Phase 1 : quantification des modeles Ollama =="
curl -s -m 10 http://$H:11434/api/tags | python3 -c "
import sys, json
for m in json.load(sys.stdin)['models']:
    d = m['details']
    print(m['name'], '|', d.get('format'), '|', d.get('family'), '|', d.get('parameter_size'), '|', d.get('quantization_level'), '|', round(m['size']/1e9, 2), 'Go')"
echo "-- ollama show qwen3:1.7b --"
curl -s -m 10 http://$H:11434/api/show -d '{"model":"qwen3:1.7b"}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('details:', json.dumps(d['details']))
mi = d.get('model_info', {})
print({k: v for k, v in mi.items() if k in ('general.file_type','general.parameter_count','qwen3.context_length','qwen3.block_count','qwen3.embedding_length')})
print('capabilities:', d.get('capabilities'))
"
echo
echo "== Brain / hypervisor (lecture seule) =="
curl -s -m 5 http://brain.example.lan:8188/mode; echo
for h in brain.example.lan frontend.example.lan; do
  echo "-- $h --"
  ssh -o BatchMode=yes -o ConnectTimeout=5 $h 'hostname; uptime -p; free -g | sed -n 2p; (nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null || echo "pas de GPU ici"); docker ps --format "{{.Names}} {{.Status}}" 2>/dev/null | head -20; systemctl is-active vllm 2>/dev/null; which ollama 2>/dev/null; nproc; df -h / /var 2>/dev/null | tail -2' 2>&1 | head -30
done
