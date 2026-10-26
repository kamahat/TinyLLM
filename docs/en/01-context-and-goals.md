# 01 — Context and goals

## The question

Can a **speech-to-text (STT) model, a large language model (LLM) and a text-to-speech (TTS) model run together, locally, with no cloud, on a small and cheap machine** — and be good enough to control a smart home by voice?

"Small" here means a mini-PC with an **Intel Core i3-6100T (2 cores / 4 threads, AVX2), about 7 GB of RAM and no GPU**. "No cloud" means that audio, text and device commands never leave the house: no hosted speech API, no hosted LLM, no hosted voice.

The use case is [Home Assistant](https://www.home-assistant.io/) *Assist*: a wall tablet listens for the wake word "hey Jarvis", the sentence is transcribed, a small LLM decides which Home Assistant **tool** to call (turn a light on, close a shutter, start a script, read a sensor), Home Assistant runs it, and a synthetic voice confirms. The assistant should also answer a few questions about the outside world, so a private web search was added.

## Why it is hard on small hardware

| Constraint | Consequence |
|---|---|
| No GPU, 4 CPU threads | Prompt processing runs at about **46 tokens/s** and generation at about **8 tokens/s** for a 1.7B model (Q4_K_M). A prompt of 3,000 tokens takes more than a minute when the cache is cold |
| ~7 GB of RAM shared by STT, TTS, LLM and the OS | Only one LLM can stay loaded; small models only |
| Small LLMs are weak at tool calling | A stock 1.7B model scores **18 %** on a French smart-home benchmark: it writes the tool name as text instead of calling it |
| The smart-home framework sends a **long prompt** (25 tools, ~3,000 tokens) | Latency is dominated by *reading* the prompt, not by generating the answer |
| A voice assistant can act on the physical world | A wrong tool call has real consequences, so failures must be safe, not just rare |

## What this study contains

- The **architecture** of a working, fully local chain (STT + LLM + TTS + private web search) — [02](02-architecture.md).
- The **techniques compared**: a stock small LLM, **LoRA fine-tuning**, **RAG** (retrieval of the relevant devices), a **compact prompt** with deterministic guard-rails, and a private **web search** tool — [03](03-methods.md).
- The **models compared** — Qwen3-1.7B (five training iterations), Qwen3-0.6B and CroissantLLM 1.3B for the LLM; Whisper tiny, base and small for STT; Piper for TTS — with a French benchmark and measured latencies — [04](04-results.md).
- **Advantages and drawbacks** of the local approach and of each technique — [05](05-pros-and-cons.md).
- **Lessons, incidents and limits** — [06](06-lessons-and-limits.md) — and a condensed **reproduction guide** — [07](07-reproduce.md).

## What was *not* done

Stated up front so the results are not over-read: the Qwen3-4B model and other quantization levels (Q1–Q3) were **not benchmarked**; speech models were evaluated on **synthetic speech** (not real microphone recordings); all benchmark sentences are in **French** and the numbers come from **one machine and one home**. See [06](06-lessons-and-limits.md).
