class AlpacaReadError(RuntimeError):
    pass


class AlpacaRateLimitError(AlpacaReadError):
    pass


class AlpacaNetworkError(AlpacaReadError):
    pass


class AlpacaAuthenticationError(AlpacaReadError):
    pass
