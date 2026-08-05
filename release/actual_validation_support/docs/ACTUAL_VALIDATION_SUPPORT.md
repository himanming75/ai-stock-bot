# P2/P3/P4 Actual Validation Support

This package does not add a roadmap stage.

It prepares the operator workflow for the existing actual validations:

1. submit one explicit P2 Paper order;
2. capture the returned Client Order ID;
3. poll Alpaca by Client Order ID;
4. write P2 actual validation;
5. read account, positions, and open orders;
6. run P3 actual synchronization and write validation;
7. record P4 prerequisite validation;
8. proceed to P5 actual multi-session qualification.

Installation uses no network and submits zero orders.
