from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json


@dataclass
class OrderTicket:

    version: str

    symbol: str

    side: str

    quantity: int

    reference_price: float

    estimated_value: float

    order_type: str

    time_in_force: str

    status: str

    execution_blocked: bool

    manual_approval_required: bool

    broker_order_created: bool

    paper_order_created: bool

    live_order_created: bool

    created_at: str

    reasons: list

    warnings: list

    next_actions: list


def build_order_ticket(position_sizing):

    if position_sizing.position_action == "ENTER_LONG":

        side = "BUY"

    elif position_sizing.position_action == "EXIT_LONG":

        side = "SELL"

    else:

        side = "NONE"

    quantity = int(position_sizing.proposed_shares)

    estimated_value = round(
        quantity * position_sizing.latest_close,
        2,
    )

    ticket = OrderTicket(

        version="V9.5",

        symbol=position_sizing.symbol,

        side=side,

        quantity=quantity,

        reference_price=position_sizing.latest_close,

        estimated_value=estimated_value,

        order_type="MARKET",

        time_in_force="DAY",

        status="WAITING_MANUAL_APPROVAL",

        execution_blocked=True,

        manual_approval_required=True,

        broker_order_created=False,

        paper_order_created=False,

        live_order_created=False,

        created_at=datetime.now().isoformat(),

        reasons=[

            "Position sizing completed.",
            "Risk Manager approved.",
            "Manual approval required before execution."

        ],

        warnings=[

            "No broker API called.",
            "No paper trade created.",
            "No live trade created."

        ],

        next_actions=[

            "Review order.",
            "Approve manually.",
            "Send to broker module in future versions."

        ]

    )

    return ticket


def save_order_ticket(ticket):

    folder = Path("output/trading_engine/order_ticket")

    folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report = folder / f"{ticket.symbol}_order_ticket_{timestamp}.json"

    latest = folder / f"{ticket.symbol}_order_ticket_latest.json"

    with open(report, "w", encoding="utf-8") as f:
        json.dump(asdict(ticket), f, indent=4)

    with open(latest, "w", encoding="utf-8") as f:
        json.dump(asdict(ticket), f, indent=4)

    return report, latest