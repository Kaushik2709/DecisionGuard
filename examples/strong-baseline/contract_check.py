"""Consumer expectations against the real local provider adapter and response schema."""

import json
from pathlib import Path

from api import provider_amount
from jsonschema import Draft202012Validator

schemas = json.loads(Path("openapi.json").read_text(encoding="utf-8"))["components"]["schemas"]
request = Draft202012Validator(schemas["CheckoutRequest"])
response = Draft202012Validator(schemas["CheckoutResponse"])
for amount, expected in [(0, 0), (1, 100), (499, 49900), (1.25, 125)]:
    request.validate({"amount": amount})
    result = {"provider_amount": provider_amount(amount), "currency": "INR"}
    response.validate(result)
    assert result["provider_amount"] == expected
