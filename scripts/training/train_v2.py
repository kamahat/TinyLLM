#!/usr/bin/env python3
"""LoRA v2 : prompt + outils EXACTS de HA, tours multiples (appel d outil, puis reponse apres resultat/erreur)."""
import argparse, json, random, time, math, torch
from transformers import AutoTokenizer, AutoModelForCausalLM, get_cosine_schedule_with_warmup
from peft import LoraConfig, get_peft_model
ap = argparse.ArgumentParser()
ap.add_argument("--base", default="Qwen/Qwen3-1.7B"); ap.add_argument("--out", required=True); ap.add_argument("--data", default="/var/lib/tinyllm/data")
ap.add_argument("--n1", type=int, default=2300); ap.add_argument("--n2", type=int, default=1500); ap.add_argument("--lr", type=float, default=2e-4); ap.add_argument("--accum", type=int, default=8)
ap.add_argument("--r", type=int, default=32); ap.add_argument("--maxlen", type=int, default=5632); ap.add_argument("--epochs", type=float, default=1)
a = ap.parse_args(); random.seed(3); torch.manual_seed(3)
D = a.data + "/"; rows = json.load(open(D + "train_v2.json")); TOOLS = json.load(open(D + "ha_real_prompt.json"))["tools"]
tok = AutoTokenizer.from_pretrained(a.base)
def tools_for(used):
    if random.random() < 0.12:
        keep = [t for t in TOOLS if t["function"]["name"] in used or random.random() > 0.25]; return keep or TOOLS
    return TOOLS
def msgs_upto(ex, nsteps):
    m = [{"role": "system", "content": ex["system"]}, {"role": "user", "content": ex["user"]}]
    for s in ex["steps"][:nsteps]:
        m.append({"role": "assistant", "content": "", "tool_calls": [{"type": "function", "function": {"name": s["tool"], "arguments": s["args"]}}]})
        m.append({"role": "tool", "content": json.dumps(s["result"], ensure_ascii=False)})
    return m
def comp_call(s): return "<tool_call>\n" + json.dumps({"name": s["tool"], "arguments": s["args"]}, ensure_ascii=False) + "\n</tool_call><|im_end|>"
def samples(ex, turn2):
    used = {s["tool"] for s in ex["steps"]}; tl = tools_for(used)
    if not turn2:
        p = tok.apply_chat_template(msgs_upto(ex, 0), tools=tl, add_generation_prompt=True, tokenize=False, enable_thinking=False)
        return (p, comp_call(ex["steps"][0]) if ex["steps"] else ex["final"] + "<|im_end|>")
    p = tok.apply_chat_template(msgs_upto(ex, len(ex["steps"])), tools=tl, add_generation_prompt=True, tokenize=False, enable_thinking=False)
    return (p, ex["final"] + "<|im_end|>")
multi = [e for e in rows if e["steps"]]
prio = [e for e in multi if e["cat"] in ("piege-erreur", "echec", "info")]; rest = [e for e in multi if e["cat"] not in ("piege-erreur", "echec", "info")]
random.shuffle(rest); t2 = prio + rest[: max(0, a.n2 - len(prio))]
random.shuffle(rows); t1 = rows[: a.n1]
pairs = [samples(e, False) for e in t1] + [samples(e, True) for e in t2]
exs = []
for p, c in pairs:
    pi = tok(p, add_special_tokens=False)["input_ids"]; ci = tok(c, add_special_tokens=False)["input_ids"]
    if len(pi) + len(ci) <= a.maxlen: exs.append((pi, ci))
print("echantillons:", len(exs), "(tour 1:", len(t1), "| tour 2:", len(t2), ") | tokens moyens:", sum(len(p) + len(c) for p, c in exs) // len(exs), "| max:", max(len(p) + len(c) for p, c in exs), flush=True)
print("EXEMPLE tour 2 (fin du prompt + completion):"); p, c = samples(t2[0], True); print(p[-600:], "-->", c, flush=True)
model = AutoModelForCausalLM.from_pretrained(a.base, dtype=torch.bfloat16, device_map={"": 0}, attn_implementation="sdpa")
model.gradient_checkpointing_enable(); model.enable_input_require_grads()
model = get_peft_model(model, LoraConfig(r=a.r, lora_alpha=2 * a.r, lora_dropout=0.05, target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], task_type="CAUSAL_LM"))
steps = int(len(exs) * a.epochs / a.accum); opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
sch = get_cosine_schedule_with_warmup(opt, int(0.05 * steps), steps); model.train(); t0 = time.time(); step = micro = n = 0; run = 0.0
order = []
for _ in range(math.ceil(a.epochs)): idx = list(range(len(exs))); random.shuffle(idx); order += idx
for i in order[: steps * a.accum]:
    p, c = exs[i]; ids = torch.tensor([p + c], device="cuda"); lab = torch.tensor([[-100] * len(p) + c], device="cuda")
    loss = model(input_ids=ids, labels=lab).loss; (loss / a.accum).backward(); run += loss.item(); n += 1; micro += 1
    if micro % a.accum == 0:
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sch.step(); opt.zero_grad(set_to_none=True); step += 1
        if step % 10 == 0 or step == steps:
            el = time.time() - t0; print("etape %d/%d | perte %.4f | %.0fs | reste ~%.0f min" % (step, steps, run / n, el, (steps - step) * el / step / 60), flush=True); run = 0.0; n = 0
model.save_pretrained(a.out + "/adapter"); merged = model.merge_and_unload(); merged.save_pretrained(a.out + "/merged", safe_serialization=True); tok.save_pretrained(a.out + "/merged")
print("TRAIN_OK", a.out, flush=True)
