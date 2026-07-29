# Run from C:\stock-bot
python .\tools\handoff_adapter_v58_2.py `
  --handoff v54_to_v55 `
  --source .\release\v58_1\stages\v54_signal.json `
  --template .\tools\position_sizing_input_sample_v55_0.json `
  --output .\release\v58_2\handoff\v55_input_from_v54.json

python .\tools\position_sizing_engine_v55_0.py `
  --input .\release\v58_2\handoff\v55_input_from_v54.json `
  --mode paper `
  --output .\release\v58_2\stages\v55_sizing.json

python .\tools\handoff_adapter_v58_2.py `
  --handoff v55_to_v56 `
  --source .\release\v58_2\stages\v55_sizing.json `
  --template .\tools\risk_management_input_sample_v56_0.json `
  --output .\release\v58_2\handoff\v56_input_from_v55.json

python .\tools\risk_management_engine_v56_0.py `
  --input .\release\v58_2\handoff\v56_input_from_v55.json `
  --mode paper `
  --output .\release\v58_2\stages\v56_risk.json

python .\tools\handoff_adapter_v58_2.py `
  --handoff v56_to_v57 `
  --source .\release\v58_2\stages\v56_risk.json `
  --template .\tools\trade_execution_input_sample_v57_0.json `
  --output .\release\v58_2\handoff\v57_input_from_v56.json

python .\tools\trade_execution_coordinator_v57_0.py `
  --input .\release\v58_2\handoff\v57_input_from_v56.json `
  --mode paper `
  --output .\release\v58_2\stages\v57_execution.json
