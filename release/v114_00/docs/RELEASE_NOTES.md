# Release Notes

V113.01–V114.00 introduces persistent recovery and restart handling for a single Alpaca Paper order.

A restarted process restores the saved client order ID and reconciles it against the broker through one read-only lookup. It never repeats the original submission.
