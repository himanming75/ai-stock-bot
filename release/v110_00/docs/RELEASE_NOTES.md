# Release Notes

V109.01–V110.00 introduces the Alpaca Paper Trading API client foundation.

The API contract follows Alpaca's paper domain and key-header authentication. Network reads and writes are both disabled by default. The next release will validate explicitly opted-in, read-only account/clock/position calls before any controlled paper order is considered.
