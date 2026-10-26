# 00 — Quick start

Goal: have the **whole local voice chain running in about 30 minutes**, then decide whether to go further. You need no GPU for this guide.

> **Be honest with yourself about step 3.** With a *stock* model (no fine-tuning) the assistant is easy to start but unreliable: it scored **18 %** on our smart-home benchmark. Fine-tuning ([step 6](#6-make-it-reliable-train-your-own-model)) is what makes it work (**96 %**). The quick start gets you the plumbing; training gets you the quality.

## What you need

| | Minimum | Comfortable |
|---|---|---|
| Machine | x86-64, 4 CPU threads, **6 GB RAM**, 10 GB disk | the study used an Intel i3-6100T, ~7 GB RAM |
| Software | Docker + Docker Compose | — |
| Home Assistant | a recent version with the **Ollama** and **Wyoming** integrations | + the Companion app on a tablet for a wake word |
| GPU | not needed to run | one 12 GB GPU for training your own model (~1 h) |

## 1. Get the code

```bash
git clone https://github.com/kamahat/TinyLLM.git
cd TinyLLM/quickstart
```

## 2. Start the services

```bash
# a private secret for the local search engine
sed -i "s/CHANGE_ME/$(openssl rand -hex 32)/" searxng-settings.yml

# optional: the town used for weather questions, and the model name
export HOME_PLACE="Paris"        # default: Paris
export LLM_MODEL="qwen3:1.7b"    # default: qwen3:1.7b

docker compose up -d
docker compose ps
```

This starts five containers: **Ollama** (LLM), **Whisper** (speech-to-text), **Piper** (text-to-speech), **SearXNG** (private web search) and the **compact proxy**. The first start downloads the speech models (a few hundred MB).

| Service | Port | Who talks to it |
|---|---|---|
| Compact proxy | `11436` | **Home Assistant** (this is the address you give it) |
| Ollama | `11434` | the proxy |
| Whisper | `10300` | Home Assistant (Wyoming) |
| Piper | `10200` | Home Assistant (Wyoming) |
| SearXNG | `127.0.0.1:8888` | the proxy only |

## 3. Download a model

```bash
docker compose exec ollama ollama pull qwen3:1.7b
curl -s http://localhost:11436/health        # -> {"ok": true, "web": true, "sim": false}
```

That is a **stock** model: good enough to see the chain work, not good enough to trust with your lights.

## 4. Connect Home Assistant

1. **Settings → Devices & services → Add integration → Ollama.** URL: `http://<your-machine>:11436` (the **proxy**, not 11434). Leave the API key empty.
2. Open the new Ollama entry → add a conversation agent. Enable **Control Home Assistant → Assist** only. Add this to the instructions: *"Always answer in French, in one short sentence."*
3. **Add integration → Wyoming Protocol**, twice: `<your-machine>:10300` (Whisper) and `<your-machine>:10200` (Piper).
4. **Settings → Voice assistants → Add assistant.** Language French, conversation agent = the Ollama agent, speech-to-text = Whisper, text-to-speech = Piper. Keep **Prefer handling commands locally** on: simple phrases ("turn on the light") are then answered in ~0.1 s without the LLM.
5. Expose the devices you want to control (**Settings → Voice assistants → Expose**).

## 5. Try it

In the Assist chat (typed or spoken), try:

- a command you made sure is *not* a simple local phrase, e.g. *"Pourrais-tu éteindre toutes les lumières du salon ?"*
- a question about the world: *"Quelle est la météo demain ?"* (answered through the private search; ~20 s on a CPU)
- a trap: *"Allume le four"* when you have no oven — the assistant should refuse, not pick another device.

First request after a start takes ~35 s (cold cache): see [Troubleshooting](#troubleshooting). Stock-model failures are expected; see step 6.

## 6. Make it reliable: train your own model

The published numbers come from a Qwen3-1.7B **fine-tuned with LoRA** on synthetic examples of *your* device list. The fine-tuned weights are not published (they encode one home's devices), but the full recipe is: [03 — Methods](03-methods.md) explains the approach and [07 — Reproduce](07-reproduce.md) gives the commands (data generation, a ~1 h LoRA run on a 12 GB GPU, GGUF export, import into Ollama). Then:

```bash
export LLM_MODEL="my-model-v5"     # the name you gave it in Ollama
docker compose up -d proxy
```

Validate **before** trusting it: no regression on the benchmark, zero loops, zero false confirmation after an error ([07](07-reproduce.md#5-validate-before-connecting-nothing-is-executed)).

## 7. Measure your own machine (optional)

The scripts of the study live in `scripts/stt_tts/` (Wyoming client, a corpus generator that uses your Piper, and a Whisper benchmark). They are **research scripts**: they use absolute paths under `/opt/tinyllm` and the benchmark starts temporary containers over SSH, so edit the constants at the top before running them (`PIPER_HOST`, `PIPER_PORT`, the data path). Compare your numbers with [04 — Results](04-results.md): on our reference machine Whisper `small` needs ~3 s per utterance and Piper ~0.2 s.

## Optional: faster speech recognition

Whisper `small` costs ~3 s per utterance on a CPU. A **streaming** engine answers ~0.1 s after you stop speaking, with a higher word error rate but nearly the same share of correct commands in our (synthetic-speech) tests. In `docker-compose.yml`, replace the `whisper` service's `command` with the commented alternative (`--stt-library sherpa --sherpa-streaming … kroko …`), then `docker compose up -d whisper`. **Test it with your own voice first** — see [04 — Results](04-results.md).

## Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| First answer takes 30–60 s, then it is fast | cold prompt cache | normal after every restart; send one request to warm up |
| "No answer" / timeout on the first sentences | same, with the framework's 3,000-token prompt | point Home Assistant at the **proxy** (11436), not Ollama |
| The assistant says "device not found" for a device you have | it is not exposed to Assist, or its name is empty | expose it and give it an alias |
| Web questions say "could not find a reliable answer" | the snippets contained no figure (by design) | rephrase, or accept the honest answer |
| Web questions say "could not reach the Internet" | SearXNG down or rate-limited | `docker compose logs searxng`; wait and retry |
| It answers in English | agent instructions | add "Always answer in French" to the agent |
| Stock model calls the wrong tool or none | no fine-tuning | step 6 |

## Repository map

| Path | Content |
|---|---|
| `quickstart/` | this guide's compose file and search-engine settings |
| `docs/en`, `docs/fr` | the study, in two languages |
| `results/` | result tables (CSV): STT, TTS, LLM |
| `data/benchmark_fr_92.json` | the 92 French benchmark phrases (generic device names) |
| `scripts/proxy` | the compact proxy (`compact_proxy.py`, `compactlib.py`, `websearch.py`) |
| `scripts/training` | data generation, LoRA training, GGUF import, the RAG experiment |
| `scripts/brain` | GPU-machine sessions (stop the GPU service, train, convert, restore) |
| `scripts/bench` | LLM benchmarks, simulation checks, warm-up |
| `scripts/stt_tts` | Whisper and Piper benchmarks (Wyoming client) |
| `scripts/ha` | Home Assistant helpers (agent, pipeline, prompt capture) |
| `scripts/deploy` | compose files used in production |

Script comments are mostly in French; host names, paths and device names are anonymized placeholders (`*.example.lan`, `/opt/tinyllm`): adapt them.
