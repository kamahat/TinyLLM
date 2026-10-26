#!/usr/bin/env python3
"""LoRA format COMPACT, pour Qwen3 ou CroissantLLM. Rendu par compactlib (identique au proxy)."""
import argparse, json, random, time, math, sys, os, torch
sys.path.insert(0, "/var/lib/tinyllm/work")
from compactlib import *
from transformers import AutoTokenizer, AutoModelForCausalLM, get_cosine_schedule_with_warmup
from peft import LoraConfig, get_peft_model
ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True); ap.add_argument("--kind", required=True); ap.add_argument("--out", required=True); ap.add_argument("--data", default="/var/lib/tinyllm/data"); ap.add_argument("--tok-server", default="")
ap.add_argument("--n1", type=int, default=2600); ap.add_argument("--n2", type=int, default=1700); ap.add_argument("--lr", type=float, default=2e-4); ap.add_argument("--accum", type=int, default=8)
ap.add_argument("--r", type=int, default=32); ap.add_argument("--maxlen", type=int, default=2000); ap.add_argument("--epochs", type=float, default=1)
a = ap.parse_args(); random.seed(9); torch.manual_seed(9)
D = a.data + "/"; rows = json.load(open(D + os.environ.get("TRAIN_FILE", "train_v4c.json"))); T = compact_tools(json.load(open(D + "ha_tablet_prompt.json"))["tools"])
tok = AutoTokenizer.from_pretrained(a.base)
import urllib.request
def sv_tok(text):
    r = urllib.request.Request(a.tok_server + "/tokenize", data=json.dumps({"content": text, "add_special": False, "parse_special": True}).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())["tokens"]
def enc(text): return sv_tok(text) if a.tok_server else tok(text, add_special_tokens=False)["input_ids"]
def tools_for(ex):
    used = {s["tool"] for s in ex["steps"]}
    return [t for t in T if t["function"]["name"] in used or random.random() > 0.15] if random.random() < 0.10 else T
def base_msgs(ex): return [{"role": "system", "content": ex["system"]}] + ex["hist"] + [{"role": "user", "content": ex["user"]}]
def pair(ex, turn2):
    m = base_msgs(ex)
    if not turn2: return render(m, tools_for(ex), True, a.kind), (call_text(ex["steps"][0]["tool"], ex["steps"][0]["args"]) if ex["steps"] else ex["final"]) + stop_token(a.kind)
    for s in ex["steps"]:
        m.append({"role": "assistant", "content": "", "tool_calls": [{"function": {"name": s["tool"], "arguments": s["args"]}}]}); m.append({"role": "tool", "content": s["result"]})
    return render(m, tools_for(ex), True, a.kind), ex["final"] + stop_token(a.kind)
multi = [e for e in rows if e["steps"]]; prio = [e for e in multi if e["cat"] in ("piege-erreur", "echec", "info", "web")]; rest = [e for e in multi if e["cat"] not in ("piege-erreur", "echec", "info", "web")]
random.shuffle(prio); random.shuffle(rest); t2 = (prio + rest)[: a.n2]; random.shuffle(rows); t1 = rows[: a.n1]
BOS = [tok.bos_token_id] if a.kind == "gemma" else []   # Gemma : BOS ajoute par llama.cpp a l inference -> meme sequence a l entrainement
pairs = [pair(e, False) for e in t1] + [pair(e, True) for e in t2]; exs = []
for p, c in pairs:
    pi = BOS + enc(p); ci = enc(c)
    if len(pi) + len(ci) <= a.maxlen: exs.append((pi, ci))
print("echantillons:", len(exs), "/", len(pairs), "| tokens moyens:", sum(len(p) + len(c) for p, c in exs) // len(exs), "| max:", max(len(p) + len(c) for p, c in exs), flush=True)
print("exemple tour 2 :", pairs[-1][0][-300:].replace(chr(10), " / "), "-->", pairs[-1][1], flush=True)
model = AutoModelForCausalLM.from_pretrained(a.base, dtype=torch.bfloat16, device_map={"": 0}, attn_implementation=("eager" if a.kind == "gemma" else "sdpa")); model.gradient_checkpointing_enable(); model.enable_input_require_grads()
model = get_peft_model(model, LoraConfig(r=a.r, lora_alpha=2 * a.r, lora_dropout=0.05, target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], task_type="CAUSAL_LM"))
steps = max(1, int(len(exs) * a.epochs / a.accum)); opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
sch = get_cosine_schedule_with_warmup(opt, int(0.05 * steps), steps); model.train(); t0 = time.time(); step = micro = n = 0; run = 0.0; order = []
for _ in range(math.ceil(a.epochs)): idx = list(range(len(exs))); random.shuffle(idx); order += idx
for i in order[: steps * a.accum]:
    p, c = exs[i]; ids = torch.tensor([p + c], device="cuda")
    out = model(input_ids=ids, logits_to_keep=len(c) + 1); loss = torch.nn.functional.cross_entropy(out.logits[0, :-1].float(), ids[0, -len(c):]); (loss / a.accum).backward(); run += loss.item(); n += 1; micro += 1
    if micro % a.accum == 0:
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sch.step(); opt.zero_grad(set_to_none=True); step += 1
        if step % 10 == 0 or step == steps:
            el = time.time() - t0; print("etape %d/%d | perte %.4f | %.0fs | reste ~%.0f min" % (step, steps, run / n, el, (steps - step) * el / step / 60), flush=True); run = 0.0; n = 0
model.save_pretrained(a.out + "/adapter"); merged = model.merge_and_unload(); merged.save_pretrained(a.out + "/merged", safe_serialization=True); tok.save_pretrained(a.out + "/merged")
print("TRAIN_OK", a.out, flush=True)
