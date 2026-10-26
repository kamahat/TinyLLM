set -e
export TMPDIR=/var/lib/tinyllm/tmp PIP_CACHE_DIR=/var/lib/tinyllm/pipcache
cd /var/lib/tinyllm
mkdir -p work models data
[ -d venv ] || python3 -m venv venv
. venv/bin/activate
pip install -q -U pip wheel setuptools
pip install -q torch --index-url https://download.pytorch.org/whl/cu128
pip install -q "transformers>=4.51" peft trl datasets accelerate sentence-transformers safetensors sentencepiece gguf numpy
python - <<'PY'
import torch, transformers, peft, trl
print("torch", torch.__version__, "cuda", torch.version.cuda, "dispo", torch.cuda.is_available())
print("arch", torch.cuda.get_arch_list())
print("transformers", transformers.__version__, "peft", peft.__version__, "trl", trl.__version__)
PY
echo SETUP_OK
