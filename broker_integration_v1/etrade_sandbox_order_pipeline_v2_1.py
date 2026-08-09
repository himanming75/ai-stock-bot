from __future__ import annotations

from .etrade_sandbox_order_builder_v2_1 import (
    build_equity_preview_payload,
    build_equity_place_payload,
    extract_preview_id,
    extract_order_id,
)


class ETradeSandboxOrderPipeline:
    def __init__(self,transport):
        self.transport=transport

    def preview(self,account_id_key,request,client_order_id=None):
        payload=build_equity_preview_payload(request,client_order_id)
        path=f"/accounts/{account_id_key}/orders/preview.json"
        response=self.transport.post_json(path,payload)
        preview_id=extract_preview_id(response)
        return {
            "status":"PASS_SANDBOX_PREVIEW",
            "account_id_key":account_id_key,
            "client_order_id":payload["PreviewOrderRequest"]["clientOrderId"],
            "preview_id":preview_id,
            "preview_payload":payload,
            "raw_response":response,
            "real_money_moved":False,
        }

    def place_from_preview(self,account_id_key,preview_result):
        payload=build_equity_place_payload(
            preview_result["preview_payload"],
            preview_result["preview_id"],
        )
        path=f"/accounts/{account_id_key}/orders/place.json"
        response=self.transport.post_json(path,payload)
        order_id=extract_order_id(response)
        return {
            "status":"PASS_SANDBOX_PLACE",
            "account_id_key":account_id_key,
            "order_id":order_id,
            "preview_id":preview_result["preview_id"],
            "place_payload":payload,
            "raw_response":response,
            "real_money_moved":False,
        }

    def preview_and_place(self,account_id_key,request,client_order_id=None):
        p=self.preview(account_id_key,request,client_order_id)
        x=self.place_from_preview(account_id_key,p)
        return {"preview":p,"place":x}
