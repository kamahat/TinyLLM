# 05 — Advantages and drawbacks

## Fully local vs cloud

| | Fully local (this study) | Cloud speech + LLM |
|---|---|---|
| **Privacy** | Audio, text and commands never leave the house; web queries are anonymized and the log is purged after 7 days | Voice and requests are processed by a third party |
| **Availability** | Works without Internet for all home control; only web questions need a connection | Fails when the connection or the provider fails |
| **Cost** | Hardware you already own; no per-request fee; electricity only | Subscription or per-token fees |
| **Latency** | Home orders ~5–10 s end to end on a CPU-only mini-PC; web questions ~20 s | Typically 1–3 s |
| **Quality** | A 1.7B model is excellent at *one narrow task* (tool calling on a known device list), weak at general knowledge, arithmetic and multi-step reasoning | Much stronger general assistant |
| **Control** | You own the prompt, the model, the guard-rails and the failure behaviour | Behaviour changes without notice |
| **Effort** | Substantial: data generation, training, benchmarking, a proxy to maintain | Almost none |
| **Safety** | Failures can be made **deterministic and safe** (guard-rails, simulation, refusal on error) | Opaque |

**Verdict.** Local is the right choice when privacy, independence and predictability matter and the tasks are *narrow and structured* (home control). It is the wrong choice if the goal is a general-purpose conversational assistant: a small model on a CPU will not match a cloud model, and ~20 s for a web answer is slow.

## Technique by technique

| Technique | Advantages | Drawbacks | Verdict here |
|---|---|---|---|
| **No training** (stock model) | Nothing to build | 18 % on the benchmark; writes the tool name as text | Not usable |
| **LoRA fine-tuning** | Turns a 1.7B model from 18 % to ~96 % on tool calls; small adapter; ~1 h on a consumer GPU; improves French behaviour and refusals; can encode "stop after an error" | Needs a GPU for training, synthetic data and a benchmark; must be **retrained when devices change**; risk of overfitting to the data style | **Essential** |
| **RAG** (retrieve relevant devices) | Scales to hundreds of devices; no retraining when devices change | Extra component (embedder, index); retrieval errors become tool errors; **a changing prompt discards the LLM cache** (≈ +25 s per request on CPU) | Not worth it below ~100 devices; keep for later |
| **Compact prompt + proxy** | Prompt ÷ 2.3; stable cache; hard limits on loops, length and tool names; enables safe testing | One more service to run; the model is coupled to the proxy's format | **Biggest gain** |
| **Deterministic guard-rails** | Exact, instant, testable; fix failures that more training does not | They hide model weaknesses instead of removing them; each is a special case | **Strongly recommended** |
| **Local web search** | Private, no API key | Rate-limited engines; snippets often lack the exact figure; +12–18 s over a command | Useful, with honest "not found" answers |
| **Smaller model** (0.6B) | ~40 % faster; 0.4 GB file | More wrong confirmations; weaker at reading snippets | Viable if latency dominates |
| **Bigger model** (4B, not measured) | Probably better at reading web snippets | Latency ×2–2.5 on this CPU (estimate), larger files | A GPU would be the real lever |

## What each layer is *for*

- **STT** decides what the system hears, and is the **biggest fixed latency** (~3 s with Whisper `small`). Whisper `small` is clearly more accurate than `tiny`/`base`, and a short **vocabulary prompt** helps. A **streaming** engine answers in ~0.1 s after you stop speaking with a higher word error rate but nearly the same share of correct commands (on synthetic speech) — [04](04-results.md).
- **The LLM** decides what to do. Fine-tuning is what makes a tiny model reliable at this single task.
- **Guard-rails and the proxy** decide what is *allowed* to happen and what is said back.
- **TTS** is the cheapest part: Piper synthesizes a sentence in about 0.2 s on this CPU.
