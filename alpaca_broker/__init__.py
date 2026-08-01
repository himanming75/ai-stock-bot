"""Safe Alpaca paper broker integration foundation."""

from .config import AlpacaPaperConfig, CredentialLoader
from .errors import (
    AlpacaBrokerError,
    AlpacaConfigurationError,
    AlpacaHttpError,
    AlpacaNetworkDisabledError,
    AlpacaResponseError,
)
from .models import (
    BrokerAccount,
    BrokerClock,
    BrokerOrder,
    BrokerPosition,
    BrokerResponse,
    ReconciliationSummary,
)
from .client import AlpacaPaperClient
from .reconciliation import BrokerPortfolioReconciler
from .transport import HttpTransport, UrllibHttpTransport
from .read_validation import (
    ControlledPaperReadValidator,
    ControlledReadReport,
    READ_CONFIRMATION_ENV,
    READ_CONFIRMATION_TEXT,
    READ_OPT_IN_ENV,
)
from .order_optin import (
    ALLOWED_SYMBOLS,
    MAX_NOTIONAL,
    MAX_QUANTITY,
    ControlledOrderPlan,
    ControlledOrderReport,
    ControlledPaperOrderOptIn,
    WRITE_CONFIRMATION_ENV,
    WRITE_CONFIRMATION_TEXT,
    WRITE_OPT_IN_ENV,
)

__all__ = [
    "AlpacaPaperConfig",
    "CredentialLoader",
    "AlpacaBrokerError",
    "AlpacaConfigurationError",
    "AlpacaHttpError",
    "AlpacaNetworkDisabledError",
    "AlpacaResponseError",
    "BrokerAccount",
    "BrokerClock",
    "BrokerOrder",
    "BrokerPosition",
    "BrokerResponse",
    "ReconciliationSummary",
    "AlpacaPaperClient",
    "BrokerPortfolioReconciler",
    "HttpTransport",
    "UrllibHttpTransport",
    "ControlledPaperReadValidator",
    "ControlledReadReport",
    "READ_CONFIRMATION_ENV",
    "READ_CONFIRMATION_TEXT",
    "READ_OPT_IN_ENV",
    "ALLOWED_SYMBOLS",
    "MAX_NOTIONAL",
    "MAX_QUANTITY",
    "ControlledOrderPlan",
    "ControlledOrderReport",
    "ControlledPaperOrderOptIn",
    "WRITE_CONFIRMATION_ENV",
    "WRITE_CONFIRMATION_TEXT",
    "WRITE_OPT_IN_ENV",
]
