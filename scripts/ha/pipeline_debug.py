import sys, json
from datetime import datetime
sys.path.insert(0, "/opt/tinyllm/ha")
from ws import ws
pls = {p["id"]: p["name"] for p in ws({"type": "assist_pipeline/pipeline/list"})["result"]["pipelines"]}
for pid, name in pls.items():
    r = ws({"type": "assist_pipeline/pipeline_debug/list", "pipeline_id": pid})
    runs = r.get("result", {}).get("pipeline_runs", [])
    print("==", name, "| runs:", len(runs))
    for run in runs[-6:]:
        d = ws({"type": "assist_pipeline/pipeline_debug/get", "pipeline_id": pid, "pipeline_run_id": run["pipeline_run_id"]})
        ev = d.get("result", {}).get("events", [])
        def t(e): return datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).timestamp()
        out = {}; t0 = t(ev[0]) if ev else 0
        for e in ev:
            ty = e["type"]; dat = e.get("data") or {}
            if ty == "stt-start": out["stt_start"] = round(t(e) - t0, 1)
            if ty == "stt-end": out["stt_end"] = round(t(e) - t0, 1); out["heard"] = (dat.get("stt_output") or {}).get("text")
            if ty == "intent-start": out["intent_start"] = round(t(e) - t0, 1); out["engine"] = dat.get("engine")
            if ty == "intent-end": out["intent_end"] = round(t(e) - t0, 1); out["reply"] = ((dat.get("intent_output") or {}).get("response", {}).get("speech", {}).get("plain", {}) or {}).get("speech")
            if ty == "tts-end": out["tts_end"] = round(t(e) - t0, 1)
            if ty == "error": out["error"] = dat
        print(run.get("timestamp"), json.dumps(out, ensure_ascii=False)[:520])
