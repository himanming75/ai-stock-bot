class AlpacaBrokerError(RuntimeError):
    """Base broker integration error."""


class AlpacaConfigurationError(AlpacaBrokerError):
    pass


class AlpacaNetworkDisabledError(AlpacaBrokerError):
    pass


class AlpacaHttpError(AlpacaBrokerError):
    def __init__(self, status_code: int, message: str, request_id: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


class AlpacaResponseError(AlpacaBrokerError):
    pass
