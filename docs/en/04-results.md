# 04 — Results

Hardware: Intel Core i3-6100T (4 threads, AVX2), ~7 GB RAM, **no GPU**; Ollama 0.40.x, GGUF Q4_K_M; Whisper and Piper through the Wyoming protocol. Raw CSV files are in [`../../results/`](../../results/). The LLM benchmark sentences are in [`../../data/benchmark_fr_92.json`](../../data/benchmark_fr_92.json) (names of devices are generic in the published copy; the numbers below come from the original, private, device names).

> **Read the limits first** ([06](06-lessons-and-limits.md)): one machine, French only, a small benchmark, and **synthetic speech** for STT.

## 1. Speech-to-text (Whisper, and two alternative engines)

92 spoken commands synthesized with Piper (clean) and the same audio with white noise added at 15 dB signal-to-noise ratio. `WER` = word error rate. Latency = time between the end of the speech and the transcript (the streaming engine receives the audio at real-time pace, as from a microphone). The last column replays 46 of the benchmark phrases through the production LLM using the **transcribed** text instead of the exact text (reference with the exact text: 43/46, 93 %).

| STT engine | WER, clean audio | WER, noisy audio (15 dB) | Latency after speech ends | Real-time factor | Correct commands end to end, clean / noisy |
|---|---|---|---|---|---|
| Whisper tiny-int8 + vocabulary prompt | 31.2 % | 45.4 % | 0.68 s | 0.38 | 35/46 (76 %) / – |
| Whisper base-int8 + vocabulary prompt | 16.0 % | 24.4 % | 1.41 s | 0.79 | 40/46 (87 %) / – |
| **Whisper small-int8 + vocabulary prompt (production)** | 6.5 % | 11.5 % | 3.04 s | 1.71 | 44/46 (96 %) / 43/46 (93 %) |
| Whisper small-int8, no prompt | 9.6 % | 13.5 % | 3.12 s | 1.75 | – / – |
| Parakeet TDT 0.6B v3, int8 (sherpa-onnx) | 9.2 % | 9.0 % | 0.39 s | 0.22 | 42/46 (91 %) / 42/46 (91 %) |
| **Streaming Zipformer FR, Kroko (sherpa-onnx)** | 11.7 % | 12.3 % | 0.12 s | 0.07 | 43/46 (93 %) / 43/46 (93 %) |

**Findings**
- **Whisper's latency is a fixed cost.** It stays at about 3 s (standard deviation 0.1 s) whatever the length of the utterance (0.9 to 2.8 s), because faster-whisper pads every utterance to a **30-second window** before encoding. On this CPU, `small` therefore needs ~3 s even for a one-word command. Smaller Whisper models are faster but not accurate enough (31 % and 16 % WER).
- **Engines whose cost follows the audio length are much faster.** Parakeet TDT 0.6B v3 answers in **0.39 s**; a **streaming** model (Kroko Zipformer, French, only 68 MB) answers **0.12 s after you stop speaking**, because it transcribes *while* you speak.
- **The word error rate is higher, but commands still work.** WER rises from 6.5 % (Whisper small + prompt) to 9.2 % and 11.7 %, yet the share of correct *commands* stays within one to three phrases of Whisper small (91–93 % against 93–96 %; differences of that size are noise on 46 phrases). The LLM was trained with transcription noise and Home Assistant matches device names loosely.
- **Less sensitive to noise**: Parakeet (9.2 → 9.0 %) and the streaming model (11.7 → 12.3 %) barely move at 15 dB, while Whisper small goes from 6.5 to 11.5 %.
- The **vocabulary prompt** helps Whisper `small` (WER 9.6 → 6.5 %, exact sentences 59 → 68 of 92) and costs nothing; the alternative engines have no equivalent.
- **Caveat: this is synthetic speech.** Real microphones, accents and rooms may hurt the new engines more than Whisper, which was trained on a huge amount of real speech. A **live A/B test with real voices** is the necessary next step before replacing Whisper.

## 2. Text-to-speech (Piper, `fr_FR-siwis-medium`)

| Text | n | Audio produced | First audio | Total synthesis | Real-time factor |
|---|---|---|---|---|---|
| Command sentences | 92 | 1.8 s | 0.18 s (max 0.34 s) | 0.19 s | 0.11 |
| Assistant replies | 10 | 2.7 s | 0.27 s (max 0.55 s) | 0.29 s | 0.11 |

TTS is the cheapest stage: a reply is ready in **under 0.6 s**. Other voices and TTS models were **not measured**.

## 3. LLM: from a stock model to the production model

French benchmark, first tool call (92 phrases), 2,500-token prompts:

| Stage | Result | Commands answered without a tool call | Mean latency | Prompt tokens |
|---|---|---|---|---|
| Stock Qwen3-1.7B (Q4_K_M) | 17/92 (18 %) | 72/76 | 5.8 s | 2540 |
| v1 LoRA, full prompt | 88/92 (96 %) | 0/76 | 7.2 s | 2537 |
| v1 LoRA + RAG in the user message (31 phrases) | 26/31 (84 %) | 0/25 | 7.5 s | 1896 |
| v1, exact framework request | 86/92 (93 %) | 2/76 | 6.9 s | 2528 |
| v2, exact framework request | 87/92 (95 %) | 2/76 | 7.1 s | 2528 |

Fine-tuning moves a 1.7B model from **18 % to 96 %**. "Exact framework request" is the real request captured from Home Assistant (the earlier benchmark used an approximation and flattered the model).

### Models and prompt formats compared

Tablet-prompt benchmark (46 phrases; with history = previous turns replayed; adversarial = unavailable sensors and non-existent devices; false confirmation = the model says "done" after the tool returned an error):

| Model / format | No history | With history | Commands without tool call (history) | Adversarial | False confirmations after an error | Mean latency | File size |
|---|---|---|---|---|---|---|---|
| Qwen3-1.7B v2 (framework prompt, ~3,000 tokens) | 43/46 (93 %) | 36/46 (78 %) | 7/38 | 6/6 (100 %) | n/a (loops: 0) | 7.1 s | 1.1 GB |
| Qwen3-1.7B v3 (framework prompt, ~3,000 tokens) | 43/46 (93 %) | 39/46 (85 %) | 2/38 | 6/6 (100 %) | n/a (loops: 0) | 7.8 s | 1.1 GB |
| Qwen3-1.7B v4c (compact, ~1,330 tokens) | 44/46 (96 %) | 42/46 (91 %) | 1/38 | 6/6 (100 %) | 0/33 | 5.0 s | 1.1 GB |
| CroissantLLM 1.3B v4c (HF tokenization, INVALID) | 17/46 (37 %) | 17/46 (37 %) | 0/38 | 0/6 (0 %) | 0/30 | 5.0 s | 0.87 GB |
| CroissantLLM 1.3B v4d (llama.cpp tokenization) | 42/46 (91 %) | 39/46 (85 %) | 1/38 | 6/6 (100 %) | 0/34 | 4.9 s | 0.87 GB |
| **Qwen3-1.7B v5 (compact + web) — in production** | 43/46 (93 %) | 44/46 (96 %) | 1/38 | 6/6 (100 %) | 0/33 | 4.8 s | 1.1 GB |
| Qwen3-0.6B v5 (compact + web) | 43/46 (93 %) | 42/46 (91 %) | 1/38 | 6/6 (100 %) | 0/33 | 2.9 s | 0.40 GB |

**Findings**
- The **compact prompt + proxy** is the main gain: the same Qwen3-1.7B goes from 93 %/85 % (framework prompt, v3) to **96 %/91 %** (v4c), with a prompt 2.3 times smaller and a faster answer (5.0 s instead of 7.8 s).
- **v5** adds web search without hurting orders (**96 % with history**), and was kept for production.
- **CroissantLLM 1.3B** is a respectable second (91 %/85 %), lighter (0.87 GB), but behind Qwen3; its first version was **invalid because of a tokenizer mismatch** (37 %).
- **Qwen3-0.6B** matches the 1.7B on choosing the tool without history (93 %) and is **~40 % faster** (2.9 s against 4.8 s), but loses 5 points with history. See below.

### Qwen3-0.6B versus Qwen3-1.7B (same recipe, v5)

| Measure | Qwen3-1.7B v5 | Qwen3-0.6B v5 |
|---|---|---|
| Correct tool call, no history / history | 93 % / 96 % | 93 % / 91 % |
| Adversarial, forced error | 6/6, 32/34 | 6/6, 32/34 |
| Trap phrases that triggered a tool call | 0/5 | 1/5 (a non-existent device: the framework returned an error) |
| **Spurious refusal after a successful command** (before the guard-rail) | 2/35 (no history), 5/36 (history) | **22/36**, **21/35** |
| … fixed by the `guard_success` guard-rail | 2/2 and 3/5 | 21/22 and 21/21 |
| Generation of one command | 4.8 s | **2.9 s** |
| Web question (two generations + search) | 16.5 s | **9.0 s** |
| Web answers, real queries | 15/22 | 10/22 |
| File size / memory when loaded | 1.1 GB / 1.6 GB | 0.4 GB / 0.9 GB |

The 0.6B chooses the right tool but **words the confirmation badly** (it says "device not found" after a success in 61 % of commands); only a deterministic guard-rail masks it. It is a **viable choice if latency dominates**, not the default.

## 4. Web search (Qwen3-1.7B v5, local SearXNG)

| Model, snippet setting | Routing | False triggers | Accuracy: weather / route / timetables | Real queries | Latency |
|---|---|---|---|---|---|
| **1.7B, 4 results x 230 characters (production)** | 105/105 | 0/10 general, 0/8 home | 38/38, 22/22, 19/23 | 15/22 | 16.5 s |
| 1.7B, 3 results x 170 characters | 105/105 | 0/10, 0/8 | 29/38, 19/22, 15/23 | 13/22 | 13.7 s |
| 0.6B, 4 x 230 | 105/105 | 0/10, 0/8 | 38/38, 22/22, 19/23 | 10/22 | 9.0 s |

Shorter snippets are faster but clearly less accurate: not retained. A figure the snippets do not contain is **never** read out: an early version answered "3,100 km" for a city pair (the snippets had no distance) and then "31,000 km" (a postal code read as a distance); the `grounded` guard-rail now answers "I could not find a reliable answer."

## 5. End-to-end latency budget (warm cache)

| Path | STT (small) | LLM | TTS | Total |
|---|---|---|---|---|
| Simple phrase handled by built-in local intents | ~3.0 s | 0 (no LLM, ~0.1 s) | ~0.2 s | **~3.3 s** |
| Device command through the LLM | ~3.0 s | ~4.8 s first call, +1–2 s second turn (estimate) | ~0.2 s | **~9–10 s** |
| Question answered from the web | ~3.0 s | 16.5–23 s | ~0.3 s | **~20–26 s** |
| First request after a restart (cold cache) | | + ~33–35 s | | add ~35 s; pre-warm after every restart |
| **With the streaming STT engine instead of Whisper small** | ~0.1 s | unchanged | unchanged | simple phrase **~0.4 s**, command **~6–7 s**, web **~17–23 s** |

The framework's native prompt (3,000 tokens) took **63–70 s** to process on a cold cache, which is what first made the assistant look "dead" before the compact prompt and pre-warming existed.
