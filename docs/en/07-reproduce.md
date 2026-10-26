# 07 — Reproduce it

A condensed guide. Paths and host names are placeholders: scripts use `/opt/tinyllm` and `*.example.lan`; adapt them (or set the corresponding variables) to your setup.

## 1. Services on the inference host

1. **Ollama** (`OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`). One model stays loaded; give it enough RAM.
2. **Whisper** with the Wyoming protocol (`rhasspy/wyoming-whisper`): `--model small-int8 --language fr --beam-size 1 --initial-prompt "<a sentence of your domain words>"`.
3. **Piper** with the Wyoming protocol (`rhasspy/wyoming-piper`): `--voice fr_FR-siwis-medium`.
4. **SearXNG** bound to `127.0.0.1`, JSON output enabled, generate your own `secret_key` (`scripts/deploy/searxng.settings.yml`).
5. **Compact proxy**: `scripts/proxy/{compact_proxy.py,compactlib.py,websearch.py}` in a small container, with the environment variables listed below. Always keep a copy of the previous app directory and compose file to roll back.

Proxy variables: `COMPACT_WEB` (0/1), `SEARX_URL`, `WEB_LOG`, `LOG_RETENTION_DAYS` (7), `WEB_N` (4), `WEB_CHARS` (230), `WEB_CACHE_TTL` (600), `WEB_CACHE_MAX` (100), `UPSTREAM`, `PROXY_LOG`.

## 2. Home Assistant

Add the Ollama integration pointing at the **proxy** (not at Ollama), create a conversation agent with *Assist* control only, create a pipeline (Whisper + Piper + that agent) and expose the devices you want. Set the wake word in the Companion app.

## 3. Capture the real request first

Use the simulation proxy (`compact_proxy.py --sim`) and a temporary pipeline bound to your tablet's device id to capture the *exact* prompt and tools the framework sends. Everything else (training data, benchmark) is generated from that capture.

## 4. Train (GPU machine, optional)

```bash
# data: make_train_v3.py -> make_v4c.py -> make_v5.py  (scripts/training/)
# train: scripts/brain/session_v5.sh   (stops the GPU service, LoRA r=32, converts to GGUF Q4_K_M, restores the service)
# import under a NEW name, never overwriting the model in production:
bash scripts/training/import_ollama.sh /path/to/q4_k_m.gguf my-model-v5
```

## 5. Validate before connecting (nothing is executed)

```bash
python3 scripts/bench/harness4.py --model my-model-v5 --kind qwen --every 2 --out results/none.json
python3 scripts/bench/harness4.py --model my-model-v5 --kind qwen --every 2 --hist mix --out results/hist.json
python3 scripts/bench/harness4.py --model my-model-v5 --kind qwen --adv --out results/adv.json
python3 scripts/bench/harness5_web.py my-model-v5          # web routing and accuracy
python3 scripts/stt_tts/bench_stt.py                        # STT models, clean and noisy audio
```

Switch production only after: no regression on the benchmark, **zero loops**, **zero false confirmation after a tool error**, all adversarial cases passed, no invented figure. Then warm the cache (`scripts/bench/warmup_proxy.py`) and keep the previous model and proxy for an instant rollback.

## 6. Quantize differently (optional)

```bash
# calibration text in the proxy format, then the importance matrix, then the 2-bit model
python3 scripts/training/make_calib.py
llama-imatrix -m f16.gguf -f calib.txt -o imatrix.dat -c 1536 -t 8 -ngl 0
llama-quantize --imatrix imatrix.dat f16.gguf q2_k_im.gguf Q2_K
llama-quantize f16.gguf q8_0.gguf Q8_0        # 8-bit reference
```

Import each variant into a **separate test Ollama instance** (other port) and run `scripts/bench/quant_tests.sh MODEL TAG` so the production model is never evicted.

## Rules worth keeping

1. A development agent **never executes real commands**; use the simulation proxy or call the proxy directly over HTTP.
2. Spoken test phrases are spoken by a human.
3. Never publish tokens, search-engine secrets or logs that contain spoken phrases.
