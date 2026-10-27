import type { components } from "./schema.js";

export const payload: components["schemas"]["CheckoutRequest"] = { amount: 499 };

export function assertResponse(value: unknown): asserts value is components["schemas"]["CheckoutResponse"] {
  if (typeof value !== "object" || value === null ||
      !("provider_amount" in value) || value.provider_amount !== 49900 ||
      !("currency" in value) || value.currency !== "INR") {
    throw new Error(`Expected 49900 INR; received ${JSON.stringify(value)}`);
  }
}
