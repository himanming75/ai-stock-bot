# Multi-Broker and Strategy Plugin Framework

This package provides a common broker interface, capability discovery, five
broker adapter skeletons, one offline mock broker, five strategy plugins, a
plugin registry, version comparison, and hot-swap preview.

All broker network operations raise an error. Strategy results are preview-only
and never create orders. Hot-swap and version upgrades require operator
approval and are never applied automatically.
