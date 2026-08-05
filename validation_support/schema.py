from __future__ import annotations
from typing import Any


SCHEMAS = {
    "account": {
        "required": {"id", "status", "cash", "equity", "buying_power"},
        "types": {"id": str, "status": str},
    },
    "position": {
        "required": {"symbol", "qty"},
        "types": {"symbol": str},
    },
    "order": {
        "required": {"id", "client_order_id", "status", "symbol"},
        "types": {
            "id": str,
            "client_order_id": str,
            "status": str,
            "symbol": str,
        },
    },
    "clock": {
        "required": {"timestamp", "is_open", "next_open", "next_close"},
        "types": {"is_open": bool},
    },
}


class ResponseSchemaValidator:
    def validate(
        self,
        *,
        schema_name: str,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        schema = SCHEMAS.get(schema_name)
        if schema is None:
            return {
                "schema_name": schema_name,
                "valid": False,
                "missing_fields": [],
                "type_errors": ["UNKNOWN_SCHEMA"],
            }

        missing = sorted(schema["required"] - set(value))
        type_errors = []
        for field, expected in schema["types"].items():
            if field in value and not isinstance(value[field], expected):
                type_errors.append(
                    f"{field}:EXPECTED_{expected.__name__}"
                )
        return {
            "schema_name": schema_name,
            "valid": not missing and not type_errors,
            "missing_fields": missing,
            "type_errors": type_errors,
        }
