# 06 — Lessons, incidents and limits

## Incidents that shaped the design

| Incident | Cause | Rule that followed |
|---|---|---|
| **Seven lights turned on in 45 seconds** during a test | An early model was connected with real control and tested through the conversation API. After a tool error it retried on other devices. The benchmark only measured the *first* tool call, and a test that actually executed commands had been called a "simulation" | **Never test a controlling agent live.** A simulation is a path that cannot execute (a proxy that strips tool calls). Train the *error turns* ("device not found" → refuse and stop). The framework caps tool iterations at 10 |
| Endless generation, random answers | The framework sends **no temperature and no token limit**; the server defaulted to a temperature of 0.6 and no cap | Force temperature 0 and a 160-token cap in the proxy |
| "No answer" on the first sentences | The tablet sends a **different prompt** from the API (25 tools, ~3,000 tokens); with a cold cache that is ~63 s, past the client timeout | Capture the *real* request, pre-warm the cache, shrink the prompt |
| Commands failing with a conversation history | The model **imitated the previous assistant turn** ("Turned on", a local reply with no tool call) | Train with 0–3 turns of history |
| A spoken "passes" (with an s) not recognized | Speech recognition conjugates differently from the trigger sentences; a fallback LLM without tools **claimed** it had acted | An LLM without tools must never be able to claim an action; tolerant trigger phrases |
| Latency of 25–37 s on some phrases | A sliding history discarded the LLM's prompt cache; removing the tools on turn 2 did too | Text-only short history; keep the prompt prefix stable |
| 37 % score for the French-centric model | Training tokenizer ≠ inference tokenizer (`arguments` became `a`) | Train with the inference engine's tokenization |
| Speech-to-text stuck at ~3 s whatever the sentence | faster-whisper pads every utterance to a 30-second window: a **fixed** cost per utterance | Compare engines whose cost follows the audio length (streaming); measure the **end-to-end** effect, not only the word error rate |
| Invented values ("0 degrees") on an unavailable sensor | State never seen during training | Render it as "unavailable" **and** add a deterministic guard-rail |
| "3,100 km", then "31,000 km" for a city pair | Web snippets without a figure; a postal code was read as a distance | Every number **with its unit** must appear in the snippets |

## Practical pitfalls

- The framework's real prompt is not the documented one: tool names are prefixed, the context has no states, names contain exact double spaces. **Always capture the real request** before generating training data.
- Prompt processing dominates latency on CPU: **a prompt that changes on every request breaks the cache**.
- The server keeps one model loaded: testing another model **evicts production**, which must be re-warmed afterwards.
- Background waiters such as `while pgrep -f "pattern"` launched over SSH detect **themselves** and never end; wait on a marker written to a log file instead.
- Public search engines throttle bursts (HTTP 429); mix real and synthetic snippets for training data.
- After merging a LoRA, **check that the exported folder still has the base tokenizer files** (`tokenizer.json`, `tokenizer.model`, `tokenizer_config.json`, `special_tokens_map.json`, `added_tokens.json`). Without them the GGUF converter does not mark `<start_of_turn>` as a special token: the prompt grows by 12 tokens, and the model answers a clarification question instead of calling a tool, with no error anywhere. Always compare the token count of the real prompt between the training tokenizer and the inference engine (llama.cpp `/tokenize`) before benchmarking.

## Limits of this study

- **One machine, one home, one language.** Latencies are for an Intel Core i3-6100T without a GPU; all benchmark sentences are French.
- **Synthetic speech for STT.** The STT benchmark uses TTS-generated audio (clean, and with added noise at 15 dB SNR), not real microphone recordings with accents, distance and room acoustics. Word-error rates are therefore **optimistic in absolute terms** and meaningful mainly **relative to each other**.
- **The benchmark is small** (92 phrases, 46 for the tablet-prompt benches) and written by the same author as the training data generators: no leakage of sentences, but similar style. Differences of one or two phrases are noise.
- **Not measured:** Qwen3-4B (latency estimated at ×2–2.5), quantization below Q4_K_M, other STT/TTS languages, concurrent use (the setup serves one request at a time).
- **Real queries on the web tool** are few (22) and unstable (search engines change); results are indicative.
- **Production is a single household** with a handful of dozen devices; RAG's value at larger scale is not measured.

## Open leads

- **Faster speech-to-text**: a streaming engine cuts ~2.9 s from every command at similar end-to-end accuracy on synthetic speech. Test it with **real voices** (live A/B against Whisper `small`) before adopting it; then train the LLM on that engine's typical errors.
- A **GPU on the inference host** would make a 4B–8B model as fast as today's 1.7B.
- Enrich the 0.6B training data with confirmation sentences (2–3 epochs) and measure on more real web queries.
- Ollama recently added a speech model (**Phonon**, text-to-speech): macOS first, Windows/Linux announced. Worth testing against Piper when Linux is supported (French support and CPU speed unknown).
