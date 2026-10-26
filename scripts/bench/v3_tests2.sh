#!/bin/bash
cd /opt/tinyllm
python3 scripts/sim_validate.py run 2 > logs/sim_validate_v3.log 2>&1
python3 scripts/replay_stress.py qwen3-ha-v3 > logs/replay_v3.log 2>&1
echo V3_TESTS2_DONE
