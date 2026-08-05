# R2 Windows Scheduler / Service Preparation

R2 prepares Windows deployment artifacts without registering tasks or services.

Included:

- disabled Runtime Task Scheduler XML;
- disabled Health Monitor Task Scheduler XML;
- disabled Daily Report Task Scheduler XML;
- production-gated runtime wrapper;
- operator-controlled stop request;
- task registration command preview;
- uninstall command preview;
- R1 Production Release gate.

All tasks use a future 2099 start boundary, remain disabled, use least privilege,
ignore duplicate instances, and perform zero automatic restart attempts.

Actual registration and activation remain blocked until R1 release approval.
