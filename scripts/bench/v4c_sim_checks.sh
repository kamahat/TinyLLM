#!/bin/bash
cd /opt/tinyllm
python3 scripts/sim_validate.py run 2 > logs/sim_validate_v4c.log 2>&1
N=$(wc -l < logs/proxy_sim.jsonl)
python3 /opt/tinyllm/ha/tablet_prompt_probe.py > logs/tablet_probe_v4c.log 2>&1
tail -n +$((N+1)) logs/proxy_sim.jsonl > logs/tablet_probe_v4c.jsonl
echo CHECKS_DONE
