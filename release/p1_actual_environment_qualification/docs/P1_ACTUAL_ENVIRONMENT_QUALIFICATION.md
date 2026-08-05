# P1 Actual Environment Qualification

P1 validates the actual local Windows environment before any broker network
operation is attempted.

Checks include:

- Windows operating environment;
- supported Python version;
- project virtual environment;
- Git repository and required files;
- encrypted Paper credential vault;
- imported Paper credential environment;
- Paper endpoint lock;
- credential fingerprint agreement;
- absence of separate Live credential environment variables;
- R16-R20 preparation status;
- L1 live activation safety state;
- available disk space.

P1 does not call Alpaca, read a broker account, submit a Paper order, or perform
any Live action.

A passing P1 certificate permits only the next read-only P2 broker validation.
P3 order validation and every Live action remain blocked.
