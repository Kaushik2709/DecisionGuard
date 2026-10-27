// Node 24 executes this erasable TypeScript directly; no npm dependencies.
type Checkout = { provider_amount: number; currency: string };

const amount: number = 499;
const port = Number(process.argv[2]);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid fixture port");
const url = `http://127.0.0.1:${port}/checkout`;

const unauthorized = await fetch(url, { method: "POST", body: JSON.stringify({ amount }) });
if (unauthorized.status !== 401) throw new Error("Authentication requirement lost");

const response = await fetch(url, {
  method: "POST",
  headers: { "Authorization": "Bearer fixture-token", "Content-Type": "application/json" },
  body: JSON.stringify({ amount }),
});
if (!response.ok) throw new Error(`Checkout failed: ${response.status}`);
const result = await response.json() as Checkout;
if (result.provider_amount !== 49900 || result.currency !== "INR") {
  throw new Error(`Contract mismatch: expected 49900 INR, received ${JSON.stringify(result)}`);
}
console.log(JSON.stringify({ passed: true, provider_amount: result.provider_amount, mocked_provider: true }));
