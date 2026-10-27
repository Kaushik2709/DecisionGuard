"""Real JSON Schema validation; no custom substitute for the validator."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

schemas = json.loads(Path("openapi.json").read_text(encoding="utf-8"))["components"]["schemas"]
for schema in schemas.values():
    Draft202012Validator.check_schema(schema)
request = Draft202012Validator(schemas["CheckoutRequest"])
response = Draft202012Validator(schemas["CheckoutResponse"])
request.validate({"amount": 499})
response.validate({"provider_amount": 49900, "currency": "INR"})
assert not request.is_valid({"amount": "499"})
assert not response.is_valid({"provider_amount": 49900, "currency": "USD"})
