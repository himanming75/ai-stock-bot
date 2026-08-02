# V123.01–V124.00 Autonomous Order Ledger Recovery

Robustly extracts Alpaca order fields from mappings, attributes, nested raw/data/payload objects, enums, and datetimes. Searches repository artifacts for independent historical evidence of the client or broker order ID. The actual identity result is excluded as self-referential evidence.

Classification: internal ledger or strong repository evidence = RECOVERED; broker-only client ID = EXTERNAL_ORDER; missing client ID = UNKNOWN_ORDER. Only RECOVERED permits leaving Safe Mode.

Current-stage scripts and `release/v124_00` outputs are excluded so the recovery package cannot create evidence for itself.
