# V392.09A1 Approved Snapshot Recovery

The V392.08A replay registry correctly blocks a second release attempt. That
second blocked run may overwrite the current result JSON, while the original
approved result remains in the append-only ledger.

This hotfix:

1. reads the V392.08A JSONL ledger;
2. selects the latest fully approved V392.08A record;
3. writes an immutable approved snapshot;
4. preserves the replay registry;
5. preserves the current blocked result;
6. makes V392.09A use the approved snapshot.

No queue mutation, broker network, or order submission occurs.
