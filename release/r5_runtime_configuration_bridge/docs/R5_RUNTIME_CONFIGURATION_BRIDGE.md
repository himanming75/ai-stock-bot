# R5 Strategy Profile Binding / Runtime Configuration Bridge

R5 converts a validated R4 profile into a single runtime configuration object.

Bindings prepared:

- strategy horizon and allowed symbols;
- Allocation and Multi-Account settings;
- risk limits;
- allowed order types and time-in-force;
- market-open policy;
- Paper/Live mode;
- environment variable preview.

This stage does not activate a strategy, modify the current environment, use
broker network access, enable broker write, or submit an order.

Live configuration remains gated by Paper completion and R1 production
approval.
