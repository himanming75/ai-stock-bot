from __future__ import annotations

from decimal import Decimal
import re
import secrets

from broker.contracts_v77_1 import (
    BrokerOrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)


def client_order_id():
    return secrets.token_hex(8)[:16]


def _price_type(request):
    if request.order_type is OrderType.MARKET:
        return "MARKET"
    if request.order_type is OrderType.LIMIT:
        return "LIMIT"
    if request.order_type is OrderType.STOP:
        return "STOP"
    if request.order_type is OrderType.STOP_LIMIT:
        return "STOP_LIMIT"
    raise ValueError("Unsupported E*TRADE Sandbox V2.1 order type.")


def _order_action(side):
    return "BUY" if side is OrderSide.BUY else "SELL"


def _term(tif):
    if tif is TimeInForce.DAY:
        return "GOOD_FOR_DAY"
    if tif is TimeInForce.GTC:
        return "GOOD_UNTIL_CANCEL"
    if tif is TimeInForce.IOC:
        return "IMMEDIATE_OR_CANCEL"
    raise ValueError("Unsupported E*TRADE time in force.")


def validate_client_order_id(value):
    value=str(value)
    if len(value)>20 or not re.fullmatch(r"[A-Za-z0-9]+",value):
        raise ValueError("E*TRADE clientOrderId must be <=20 alphanumeric characters.")
    return value


def build_equity_preview_payload(request, cid=None):
    if not isinstance(request,BrokerOrderRequest):
        raise TypeError("Canonical broker.contracts_v77_1.BrokerOrderRequest required.")
    request.validate()
    cid=validate_client_order_id(cid or client_order_id())

    detail={
        "allOrNone":"false",
        "priceType":_price_type(request),
        "orderTerm":_term(request.time_in_force),
        "marketSession":"REGULAR",
        "Instrument":[{
            "Product":{
                "securityType":"EQ",
                "symbol":request.symbol,
            },
            "orderAction":_order_action(request.side),
            "quantityType":"QUANTITY",
            "quantity":str(request.quantity),
        }],
    }
    if request.limit_price is not None:
        detail["limitPrice"]=str(request.limit_price)
    else:
        detail["limitPrice"]=""
    if request.stop_price is not None:
        detail["stopPrice"]=str(request.stop_price)
    else:
        detail["stopPrice"]=""

    return {
        "PreviewOrderRequest":{
            "orderType":"EQ",
            "clientOrderId":cid,
            "Order":[detail],
        }
    }


def build_equity_place_payload(preview_payload, preview_id):
    req=(preview_payload or {}).get("PreviewOrderRequest") or {}
    if not req:
        raise ValueError("PreviewOrderRequest is required.")
    if preview_id is None or str(preview_id).strip()=="":
        raise ValueError("previewId is required.")
    return {
        "PlaceOrderRequest":{
            "orderType":req["orderType"],
            "clientOrderId":req["clientOrderId"],
            "PreviewIds":[{"previewId":int(preview_id)}],
            "Order":req["Order"],
        }
    }


def extract_preview_id(response):
    body=(response or {}).get("PreviewOrderResponse") or response or {}
    ids=body.get("PreviewIds") or body.get("previewIds") or []
    if isinstance(ids,dict):
        ids=[ids]
    for row in ids:
        if isinstance(row,dict):
            value=row.get("previewId")
            if value is not None:
                return int(value)
    value=body.get("previewId")
    if value is not None:
        return int(value)
    raise ValueError("No previewId found in E*TRADE preview response.")


def extract_order_id(response):
    body=(response or {}).get("PlaceOrderResponse") or response or {}
    value=body.get("orderId")
    if value is not None:
        return str(value)
    ids=body.get("OrderIds") or body.get("orderIds") or []
    if isinstance(ids,dict):
        ids=[ids]
    for row in ids:
        if isinstance(row,dict) and row.get("orderId") is not None:
            return str(row["orderId"])
    raise ValueError("No orderId found in E*TRADE place response.")
