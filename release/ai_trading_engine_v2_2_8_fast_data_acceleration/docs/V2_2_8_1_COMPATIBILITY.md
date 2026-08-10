# V2.2.8.1 FAST Data Acceleration Compatibility

Base commit: `e7610f60`.

This package is the compatibility build for repositories that already contain
the Continuous AI Shadow Learning Pipeline V2.2.8.

It does not replace or delete the existing V2.2.8 continuous pipeline.

Existing V2.2.8 paths remain unchanged:
- ai_engine_v2/continuous_shadow_learning_pipeline_v2_2_8.py
- runtime/ai_continuous_shadow_learning_pipeline_v2_2_8/
- related START/STOP/scorecard scripts

FAST acceleration is added under separate paths:
- ai_engine_v2/fast_data_acceleration_v2_2_8.py
- runtime/ai_fast_data_acceleration_v2_2_8/
- release/ai_trading_engine_v2_2_8_fast_data_acceleration/

Safety:
- Broker trading API: OFF
- Paper order submission from this package: 0
- Existing V2.1.31 Paper universe unchanged
- Live trading: LOCKED
