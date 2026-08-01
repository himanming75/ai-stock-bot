# Release Notes

V115.01–V116.00 integrates the Paper session scheduler with the runtime lifecycle.

The integration dispatches one complete offline paper cycle during `RUN_CYCLE`, persists recovery state, supports restart recovery, and performs graceful close without enabling broker writes.
