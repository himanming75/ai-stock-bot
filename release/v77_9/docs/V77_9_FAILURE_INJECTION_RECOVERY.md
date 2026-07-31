# V77.9 Failure Injection Recovery
Base `f18e772`. Anchors: `434d6b7bca8f7683cc78146437f92b129e52cfb3079cb36a091d43a1eed6217d`, `31c147f03598cbc346573893c23adea46e6a65a3449bfac5f6466372cff8b327`, `f7e86261882217f6d9399e35ea2e8a7c3b620384ec4ad3494e226c860ce589d7`.
Injects invalid fill quantity, overfill, unknown order, cash/position/event/fill-ledger corruption, and damaged checkpoint. Restores the last good checkpoint and proves exact state-hash recovery. Offline only. Next: `V77.10 Recovery Audit Certificate`.
