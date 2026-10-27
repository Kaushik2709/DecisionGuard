import { payload, assertResponse } from "./client.ts";

const port = Number(process.argv[2]);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid fixture port");
const url = `http://127.0.0.1:${port}/checkout`;
const denied = await fetch(url, { method: "POST", body: JSON.stringify(payload) });
if (denied.status !== 401) throw new Error("Authentication requirement lost");
const response = await fetch(url, {
  method: "POST", headers: { Authorization: "Bearer fixture-token", "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});
if (!response.ok) throw new Error(`Checkout failed: ${response.status}`);
assertResponse(await response.json());
console.log(JSON.stringify({ passed: true, mocked_provider: true }));
