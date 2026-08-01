# Release Notes

V112.01–V113.00 adds post-submission validation for a single controlled Alpaca Paper order.

The validator polls by `client_order_id`, confirms terminal status, then reads the Paper account and positions. The client is required to have writes disabled.
