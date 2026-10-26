# 02 — Architecture

## Components

| Component | Where | Role |
|---|---|---|
| Android tablet | in the home | Home Assistant Companion app; **on-device** wake-word detection ("hey Jarvis"), microphone, speaker |
| Home Assistant | home server | *Assist* pipeline, conversation agent, executes tools (lights, shutters, scripts, lists…) |
| Whisper (faster-whisper, int8) | inference host | STT over the Wyoming protocol, French, `small-int8` with a short vocabulary prompt |
| Piper | inference host | TTS over Wyoming, voice `fr_FR-siwis-medium` |
| **Compact proxy** | inference host | Sits between Home Assistant and the LLM: shrinks the prompt, validates tool calls, runs the web search, applies guard-rails |
| Ollama | inference host | Serves the fine-tuned LLM on CPU (AVX2, 4 threads, flash attention) |
| SearXNG | inference host | Private meta-search engine, listening on localhost only |
| GPU machine | separate VM | **Training only** (one RTX 5070, 12 GB). It can stay powered off: production never depends on it |

The Whisper container image can also run other speech back-ends through the same Wyoming interface; two alternatives are compared in [04](04-results.md).

The inference host is a small x86 mini-PC (Intel Core i3-6100T, 4 vCPU, ~7 GB RAM for the VM, no GPU).

```mermaid
flowchart LR
    T["Tablet<br/>wake word on device"] <--> HA["Home Assistant<br/>Assist pipeline"]
    subgraph HOST["Inference host (CPU only)"]
        W["Whisper<br/>STT, French"]
        P["Piper<br/>TTS, French"]
        PX["Compact proxy<br/>smaller prompt + guard-rails"]
        O["Ollama<br/>fine-tuned LLM (LoRA, Q4_K_M)"]
        S["SearXNG<br/>private search"]
    end
    HA --> W
    HA --> P
    HA --> PX
    PX --> O
    PX --> S
    S --> NET(("Internet"))
```

## Request flow: a smart-home command

```mermaid
sequenceDiagram
    participant T as Tablet
    participant HA as Home Assistant
    participant W as Whisper
    participant PX as Compact proxy
    participant O as Ollama (LLM)
    participant P as Piper
    T->>HA: audio after the wake word
    HA->>W: audio
    W-->>HA: text ("turn on the living-room light")
    Note over HA: simple phrases are handled by built-in<br/>local intents, without any LLM (~0.1 s)
    HA->>PX: chat request (25 tools, ~3,000 tokens)
    PX->>PX: rewrite as a compact prompt (16 tools, ~1,330 tokens)
    PX->>O: raw generation, temperature 0, 160 tokens max
    O-->>PX: tool call HassTurnOn(Living-room light)
    PX-->>HA: validated tool call
    HA->>HA: execute the tool, return the result
    HA->>PX: tool result
    PX->>O: second turn (text only, tools kept for cache reuse)
    O-->>PX: "The living-room light is on."
    HA->>P: text
    P-->>T: voice
```

## Request flow: a question about the outside world

The model has a `web_search` tool that the **proxy executes itself** (Home Assistant never sees it):

```mermaid
sequenceDiagram
    participant HA as Home Assistant
    participant PX as Compact proxy
    participant O as Ollama
    participant S as SearXNG
    HA->>PX: "How warm will it be tomorrow in Nîmes?"
    PX->>O: generation 1
    O-->>PX: web_search("weather tomorrow Nîmes")
    PX->>PX: anonymize the query (strip device, room and alias names)
    PX->>S: query (in-memory cache, 10 min)
    S-->>PX: 4 snippets of 230 characters
    PX->>O: generation 2 with the snippets
    O-->>PX: one-sentence answer
    PX->>PX: check: every number + unit must appear in the snippets
    PX-->>HA: final answer (text)
```

## The compact proxy

The native prompt of the smart-home framework is about **3,000 tokens**. On this CPU a cold prompt takes ~63 s, and any change in the prompt invalidates the cache. The proxy is a small Python service (`scripts/proxy/`) that makes the LLM's job short and predictable:

| Mechanism | Effect |
|---|---|
| Compact system prompt: one line per device (`name ~ alias \| domain \| area`) | prompt −56 % (≈1,330 tokens) |
| 16 compact tools (+ `web_search`) | fewer tokens, fewer wrong tool names |
| History reduced to text, 2 turns max | the LLM cache stays valid (a sliding history used to discard it: 25–37 s per request) |
| Tools kept in the prompt on turn 2, but any **new tool call is rejected** | no loops; removing the tools used to discard the cache |
| Tool names validated against the framework's list | an invented tool name is refused |
| Temperature 0, 160 tokens max, `keep_alive: -1` | the framework sends neither a temperature nor a length limit; without this the model samples at 0.6 and can generate thousands of tokens |
| `--sim` mode | strips every tool call from the answer: used for testing without executing anything |

### Deterministic guard-rails

Small LLMs fail in repeatable ways. Instead of hoping the next fine-tune fixes them, the proxy corrects them with plain code:

| Guard-rail | Failure covered | Replacement |
|---|---|---|
| `guard_unavailable` | a value question on a sensor that is `unavailable`: the model invented "0 degrees" | "I have no recent value for …: the sensor is unavailable." |
| `guard_success` | the tool succeeded but the model says "device not found" | "Done." |
| `grounded` (web) | a number the snippets do not contain: invention, or a postal code read as a distance | "I could not find a reliable answer." |
| Turn-2 rejection | a new tool call after a tool result | text-only answer |

## Training chain (not part of production)

```mermaid
flowchart LR
    D["Synthetic data<br/>no leakage into the benchmark"] --> B["GPU machine (RTX 5070)<br/>LoRA r=32, 1 epoch"]
    B --> G["GGUF f16 then Q4_K_M<br/>llama.cpp"]
    G --> O["Import into Ollama<br/>under a new name"]
    O --> V["Validation: 92-phrase benchmark<br/>+ simulation proxy through Home Assistant"]
    V -->|owner approval| PR["Production"]
```

The training format is **exactly** the proxy's format (one shared Python module), so the model is trained on the same compact system prompts, tools and tool results it sees in production.
