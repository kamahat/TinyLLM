#!/usr/bin/env python3
"""LoRA : apprend a Qwen3 a appeler les outils Assist de HA (format <tool_call>), en francais.
Usage : train_lora.py --base Qwen/Qwen3-1.7B --out /var/lib/tinyllm/models/x [--epochs 2] [--limit N]"""
import argparse, json, random, time, os, math, torch
from transformers import AutoTokenizer, AutoModelForCausalLM, get_cosine_schedule_with_warmup
from peft import LoraConfig, get_peft_model
ap = argparse.ArgumentParser()
ap.add_argument("--base", default="Qwen/Qwen3-1.7B"); ap.add_argument("--out", required=True)
ap.add_argument("--data", default="/var/lib/tinyllm/data"); ap.add_argument("--epochs", type=float, default=2)
ap.add_argument("--lr", type=float, default=2e-4); ap.add_argument("--accum", type=int, default=8); ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--r", type=int, default=32); ap.add_argument("--maxlen", type=int, default=4096); ap.add_argument("--compact-ratio", type=float, default=0.5)
a = ap.parse_args(); random.seed(1); torch.manual_seed(1)
D = a.data + "/"
tools_raw = json.load(open(D + "ha_tools.json")); ents = json.load(open(D + "ha_exposed.json")); rows = json.load(open(D + "train_raw.json"))
if a.limit: rows = rows[: a.limit]
TOOLS = {t["name"].split("__")[-1]: {"type": "function", "function": {"name": t["name"].split("__")[-1], "description": t.get("description", ""), "parameters": t["inputSchema"]}} for t in tools_raw}
CORE = ["HassTurnOn", "HassTurnOff", "HassSetPosition", "HassLightSet", "GetLiveContext", "GetDateTime", "HassClimateSetTemperature", "HassStopMoving"]
HEAD = ("You are a voice assistant for Home Assistant.\nAnswer questions about the world truthfully.\nAnswer in plain text. Keep it simple and to the point.\n"
        "Réponds toujours en français, en une phrase courte.\n"
        "When controlling Home Assistant always call the intent tools. Use HassTurnOn to lock and HassTurnOff to unlock a lock. "
        "When controlling a device, prefer passing just name and domain. When controlling an area, prefer passing just area name and domain.\n"
        "When a user asks to turn on all devices of a specific type, ask user to specify an area, unless there is only one device of that type.\n"
        "This device is not able to start timers.\n")
def context(es):
    c = "Static Context: An overview of the areas and the devices in this smart home:\n"
    for e in es:
        c += "- names: %s\n  domain: %s\n  state: %s\n" % (e["name"], e["domain"], "\x27" + str(e["state"]) + "\x27")
        if e["area"]: c += "  areas: %s\n" % e["area"]
    return c
tok = AutoTokenizer.from_pretrained(a.base)
def build(r):
    target_names = {r["args"].get("name")} if r["args"].get("name") else set()
    compact = random.random() < a.compact_ratio
    es = list(ents)
    if compact:
        keep = [e for e in ents if e["name"] in target_names]; others = [e for e in ents if e not in keep]
        es = keep + random.sample(others, random.randint(4, 8))
    random.shuffle(es)
    names = list(TOOLS)
    if compact:
        need = [r["tool"]] if r["tool"] else []
        sel = list(dict.fromkeys(need + random.sample(CORE, random.randint(3, 6)) + random.sample(names, 2)))
    else: sel = names
    random.shuffle(sel)
    tools = [TOOLS[n] for n in sel]
    msgs = [{"role": "system", "content": HEAD + context(es)}, {"role": "user", "content": r["user"]}]
    prompt = tok.apply_chat_template(msgs, tools=tools, add_generation_prompt=True, tokenize=False, enable_thinking=False)
    comp = ("<tool_call>\n" + json.dumps({"name": r["tool"], "arguments": r["args"]}, ensure_ascii=False) + "\n</tool_call><|im_end|>") if r["tool"] else (r["text"] + "<|im_end|>")
    return prompt, comp
exs = []
for r in rows:
    p, c = build(r); pi = tok(p, add_special_tokens=False)["input_ids"]; ci = tok(c, add_special_tokens=False)["input_ids"]
    if len(pi) + len(ci) > a.maxlen: continue
    exs.append((pi, ci))
print("exemples:", len(exs), "| tokens prompt moyen:", sum(len(p) for p, _ in exs) // max(1, len(exs)), "| exemple de prompt:\n", build(rows[0])[0][-700:], "\n--> ", build(rows[0])[1], flush=True)
model = AutoModelForCausalLM.from_pretrained(a.base, torch_dtype=torch.bfloat16, device_map={"": 0}, attn_implementation="sdpa")
model.gradient_checkpointing_enable(); model.enable_input_require_grads()
model = get_peft_model(model, LoraConfig(r=a.r, lora_alpha=2 * a.r, lora_dropout=0.05, target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"], task_type="CAUSAL_LM"))
model.print_trainable_parameters()
steps = int(len(exs) * a.epochs / a.accum)
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
sch = get_cosine_schedule_with_warmup(opt, int(0.05 * steps), steps)
model.train(); t0 = time.time(); step = 0; micro = 0; run = 0.0; n = 0
order = []
for ep in range(math.ceil(a.epochs)): idx = list(range(len(exs))); random.shuffle(idx); order += idx
order = order[: steps * a.accum]
for i in order:
    p, c = exs[i]; ids = torch.tensor([p + c], device="cuda"); lab = torch.tensor([[-100] * len(p) + c], device="cuda")
    loss = model(input_ids=ids, labels=lab).loss
    (loss / a.accum).backward(); run += loss.item(); n += 1; micro += 1
    if micro % a.accum == 0:
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sch.step(); opt.zero_grad(set_to_none=True); step += 1
        if step % 10 == 0 or step == steps:
            el = time.time() - t0; print("etape %d/%d | perte %.4f | %.0fs ecoules | reste ~%.0f min" % (step, steps, run / n, el, (steps - step) * el / step / 60), flush=True); run = 0.0; n = 0
model.save_pretrained(a.out + "/adapter")
merged = model.merge_and_unload(); merged.save_pretrained(a.out + "/merged", safe_serialization=True); tok.save_pretrained(a.out + "/merged")
print("TRAIN_OK", a.out, flush=True)
