# V361–V370 Notification & Alert Routing

Stages:

- V361 Event Collection
- V362 Severity Classification
- V363 Message Normalization
- V364 Deduplication Key
- V365 Cooldown and Duplicate Suppression
- V366 Alert Priority Queue
- V367 Channel Routing Plan
- V368 Daily Notification Digest
- V369 Notification Ledger
- V370 Notification Dashboard

The module prepares notifications but sends nothing. Email, Slack, Discord,
and Webhook channels remain disabled. LOCAL_LOG means writing the normalized
event to the append-only notification ledger.

Inputs are read from Risk, Performance, System Health, and Controller
snapshots. No Controller, Runtime, Broker, or order state is modified.
