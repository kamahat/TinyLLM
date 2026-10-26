# TinyLLM — a fully local voice assistant on a small CPU-only machine

**Using small LLMs for voice control of Home Assistant — speech-to-text, LLM and text-to-speech, all running locally (no cloud) on a mini-PC without a GPU.**

🇫🇷 Version française : [README.fr.md](README.fr.md) · [docs/fr](docs/fr/)

## Context

Can a **speech-to-text model, a large language model and a text-to-speech model run together, locally, with no cloud, on a small machine** — and be good enough to control a smart home by voice? This repository documents a working answer and measures it:

- **Hardware**: Intel Core i3-6100T (4 threads, AVX2), ~7 GB RAM, **no GPU**. A separate GPU machine (RTX 5070) is used for training only.
- **Chain**: wake word on an Android tablet → **Whisper** (STT) → **Qwen3 fine-tuned with LoRA** served by **Ollama**, behind a **compact proxy** → Home Assistant executes the tool → **Piper** (TTS). A private **web search** (SearXNG) handles questions about the outside world.
- **Compared**: stock LLM, **LoRA**, **RAG**, compact prompt + guard-rails; Qwen3-1.7B / Qwen3-0.6B / CroissantLLM 1.3B; Whisper tiny / base / small; Piper.

## Headline results (French benchmark, CPU only)

| Stage | Choice | Result |
|---|---|---|
| **LLM** | stock Qwen3-1.7B | **18 %** — writes tool names as text instead of calling them |
| | + LoRA fine-tuning | **96 %** on the first tool call |
| | + compact prompt, proxy and guard-rails (v5, in production) | **93 % / 96 %** without / with history, 0 false confirmation after an error, ~5 s per command |
| | Qwen3-0.6B (same recipe) | same 93 % without history, **~40 % faster** (2.9 s), but weak confirmations |
| | CroissantLLM 1.3B | 91 % / 85 %, lighter, behind Qwen3 |
| **STT** | Whisper `small` + vocabulary prompt | **6.5 % WER** (clean), 11.5 % (noisy), ~3 s per utterance |
| | Whisper `base` / `tiny` | 16 % / 31 % WER, 1.4 s / 0.7 s |
| **TTS** | Piper `fr_FR-siwis-medium` | a reply in **~0.2–0.3 s** (real-time factor 0.11) |
| **RAG** | `multilingual-e5-base` retrieval | good retrieval (94 % hit@1) but **worse end to end** and it breaks the prompt cache — not kept below ~100 devices |
| **End to end** | | local intents ~3 s · LLM command ~9–10 s · web question ~20–26 s |

> Speech models were tested on **synthetic speech**, the benchmark is small and French-only, and numbers come from one machine. Read the [limits](docs/en/06-lessons-and-limits.md) before drawing conclusions.

## Read the study

| | English | Français |
|---|---|---|
| Context and goals | [docs/en/01](docs/en/01-context-and-goals.md) | [docs/fr/01](docs/fr/01-contexte-et-objectifs.md) |
| Architecture and diagrams | [docs/en/02](docs/en/02-architecture.md) | [docs/fr/02](docs/fr/02-architecture.md) |
| Methods: LoRA, RAG, compact proxy, web search | [docs/en/03](docs/en/03-methods.md) | [docs/fr/03](docs/fr/03-methodes.md) |
| **Results** (STT, LLM, TTS, web, latency) | [docs/en/04](docs/en/04-results.md) | [docs/fr/04](docs/fr/04-resultats.md) |
| **Advantages and drawbacks** | [docs/en/05](docs/en/05-pros-and-cons.md) | [docs/fr/05](docs/fr/05-avantages-et-inconvenients.md) |
| Lessons, incidents, limits | [docs/en/06](docs/en/06-lessons-and-limits.md) | [docs/fr/06](docs/fr/06-lecons-et-limites.md) |
| Reproduce it | [docs/en/07](docs/en/07-reproduce.md) | [docs/fr/07](docs/fr/07-reproduire.md) |

## Repository layout

| Path | Content |
|---|---|
| `docs/en`, `docs/fr` | the study, in two languages |
| `results/` | result tables as CSV: `stt_whisper.csv`, `tts_piper.csv`, `llm_models.csv`, `llm_stages.csv` |
| `data/benchmark_fr_92.json` | the 92 French benchmark phrases (generic device names) |
| `scripts/proxy` | the compact proxy (`compact_proxy.py`, `compactlib.py`, `websearch.py`) |
| `scripts/training` | data generation, LoRA training, GGUF import, the RAG experiment |
| `scripts/brain` | GPU-machine sessions (stop the GPU service, train, convert, restore) |
| `scripts/bench` | LLM benchmarks, simulation checks, warm-up |
| `scripts/stt_tts` | Whisper and Piper benchmarks (Wyoming client) |
| `scripts/ha` | Home Assistant helpers (agent, pipeline, prompt capture) |
| `scripts/deploy` | compose files for the proxy and SearXNG |

Script comments and docstrings are mostly in French. Host names, paths and device names were anonymized (`*.example.lan`, `/opt/tinyllm`, generic device names); adapt them to your setup. Raw benchmark outputs are not published (they contain private device names); the tables are.

## Safety principles kept throughout

- **No test with real execution** by a development agent: a simulation proxy strips every tool call.
- **Production never depends on the GPU machine**, which can stay off.
- Web queries are **anonymized**, logged for 7 days, with an **in-memory** cache only.
- No secret in this repository.

## License

Apache-2.0 — see [LICENSE](LICENSE).
