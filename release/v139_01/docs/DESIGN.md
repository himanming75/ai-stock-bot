# V139.01 Design

Reads V139.00 saved-state JSON only and classifies the existing order as active, terminal, or inconsistent. It never loads credentials, contacts Alpaca, submits orders, or unlocks a new cycle without a verified terminal commit.
