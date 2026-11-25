"""Kickoff Kits "Kit Assistant" – LLM agent with tool calling (Groq API).

The LLM (Groq, OpenAI-compatible chat completions API) decides which shop
tools to call. Tools run here in Python against TEST DATA. Cart, discount
and order actions are SIMULATED – nothing touches the real PrestaShop shop.
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def load_config():
    """API key: .env file next to this script, else the GROQ_API_KEY environment variable."""
    cfg = {"GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""), "GROQ_MODEL": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")}
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip():
                    cfg[k.strip()] = v.strip()
    if not cfg["GROQ_API_KEY"]:
        raise SystemExit("No Groq API key: set GROQ_API_KEY or create .env (see .env.example).")
    return cfg


# ---------------- TEST DATA (catalogue mirrors the Kickoff Kits PrestaShop shop; stock & orders are invented) ----------------
PRODUCTS = [
    {"id": 1, "name": "Home Jersey – Red #10", "category": "Club Jerseys", "colour": "red", "price": 49.99, "stock": {"S": 4, "M": 0, "L": 7, "XL": 3}},
    {"id": 2, "name": "Away Jersey – White #7", "category": "Club Jerseys", "colour": "white", "price": 44.99, "stock": {"S": 2, "M": 6, "L": 5, "XL": 0}},
    {"id": 3, "name": "Retro Lithuania Jersey – Yellow/Green #9", "category": "Retro Jerseys", "colour": "yellow/green", "price": 54.99, "stock": {"S": 1, "M": 3, "L": 2, "XL": 4}},
    {"id": 4, "name": "Goalkeeper Jersey – Green #1", "category": "Goalkeeper Jerseys", "colour": "green", "price": 39.99, "stock": {"S": 0, "M": 2, "L": 3, "XL": 1}},
]
ORDERS = [
    {"ref": "KK-1001", "email": "test.buyer@example.com", "status": "Shipped – DPD tracking LT-TEST-55821, expected 26 Nov", "items": "Away Jersey – White #7 (M)"},
    {"ref": "KK-1002", "email": "jonas.test@example.com", "status": "Processing – packing today", "items": "Retro Lithuania Jersey #9 (L)"},
]
DISCOUNTS = {"KICKOFF10": {"percent": 10, "note": "Newsletter welcome code, first order only"}}

SYSTEM_PROMPT = """You are "Kit Assistant", the customer service and shopping assistant of Kickoff Kits, a small online football jersey shop in Šiauliai, Lithuania (a PrestaShop store). This is a TEST ENVIRONMENT: cart, discount and order actions are simulated and use test data.
Rules:
- Use the tools for product, stock, order and discount facts. Never invent products, prices, stock or order details.
- The shop sells ONLY the products returned by search_products (4 Kickoff Kits jerseys). Never mention any other team, brand or product.
- Before adding anything to the cart you need the product and the size (S, M, L or XL). If the customer is vague (no product type, size or budget), FIRST call search_products with no filters, THEN ask ONE short clarifying question offering those real products (name and price) and asking for the size. Do not call add_to_cart until the details are clear.
- If a size is out of stock, say so and suggest available sizes or a similar jersey.
- Order lookups need BOTH the order reference and the email used for the order; get_order_status checks that they match. Never reveal another customer's email, address or order details.
- You may only apply a discount code the customer gives you and the tool confirms. You cannot create, invent or increase discounts.
- You cannot issue refunds, cancel orders, change prices or use admin functions. Refuse politely and point to support@kickoffkits.test.
- When you perform a simulated action, say that it was simulated in this test shop.
- Be friendly and brief: at most 5 short sentences, prices in EUR (e.g. €44.99). Plain text, no markdown tables."""

TOOL_SPECS = [
    {"type": "function", "function": {"name": "search_products", "description": "Search the Kickoff Kits catalogue. Returns products with id, name, category, colour, price (EUR) and sizes in stock. Call with no filters to list everything.",
        "parameters": {"type": "object", "properties": {"query": {"type": ["string", "null"], "description": "words like 'red', 'retro', 'goalkeeper', 'away'"}, "max_price": {"type": ["number", "null"]}, "size": {"type": ["string", "null"], "description": "S, M, L or XL"}}}}},
    {"type": "function", "function": {"name": "check_stock", "description": "Check how many units of one product are in stock in one size.",
        "parameters": {"type": "object", "properties": {"product_id": {"type": "integer"}, "size": {"type": "string", "enum": ["S", "M", "L", "XL"]}}, "required": ["product_id", "size"]}}},
    {"type": "function", "function": {"name": "add_to_cart", "description": "SIMULATED: add a product in a size to the customer's cart in this test shop. Only call when product and size are clear and in stock.",
        "parameters": {"type": "object", "properties": {"product_id": {"type": "integer"}, "size": {"type": "string", "enum": ["S", "M", "L", "XL"]}, "quantity": {"type": "integer", "minimum": 1, "maximum": 5}}, "required": ["product_id", "size"]}}},
    {"type": "function", "function": {"name": "apply_discount", "description": "SIMULATED: validate a discount code the customer gave and apply it to the cart. Cannot create new codes.",
        "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}},
    {"type": "function", "function": {"name": "get_order_status", "description": "Look up an order's status. Requires the order reference AND the email used for that order; refuses if they do not match (privacy).",
        "parameters": {"type": "object", "properties": {"order_ref": {"type": "string"}, "email": {"type": "string"}}, "required": ["order_ref", "email"]}}},
]


class ToolError(Exception):
    pass


class Session:
    """One customer conversation: chat history, simulated cart, tool-call log."""

    def __init__(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.cart = []
        self.discount = None
        self.log = []

    # ---------- tools ----------
    def search_products(self, query="", max_price=None, size=None):
        words = [w for w in str(query or "").lower().split() if w not in ("jersey", "jerseys", "shirt", "kit")]
        text = lambda p: f"{p['name']} {p['category']} {p['colour']}".lower()
        res = [p for p in PRODUCTS if all(w in text(p) for w in words)] or ([p for p in PRODUCTS if any(w in text(p) for w in words)] if words else PRODUCTS)
        if max_price:
            res = [p for p in res if p["price"] <= float(max_price)]
        if size:
            res = [p for p in res if p["stock"].get(str(size).upper(), 0) > 0]
        return [{"id": p["id"], "name": p["name"], "category": p["category"], "colour": p["colour"], "price": p["price"],
                 "sizes_in_stock": [s for s, n in p["stock"].items() if n > 0]} for p in res]

    def check_stock(self, product_id, size):
        p = next((x for x in PRODUCTS if x["id"] == int(product_id)), None)
        if not p:
            raise ToolError("Unknown product id")
        s = str(size).upper()
        return {"product": p["name"], "size": s, "units": p["stock"].get(s, 0)}

    def add_to_cart(self, product_id, size, quantity=1):
        p = next((x for x in PRODUCTS if x["id"] == int(product_id)), None)
        if not p:
            raise ToolError("Unknown product id")
        s, q = str(size).upper(), max(1, min(5, int(quantity or 1)))
        if p["stock"].get(s, 0) < q:
            raise ToolError(f"Only {p['stock'].get(s, 0)} left in size {s}")
        self.cart.append({"name": p["name"], "size": s, "qty": q, "price": p["price"]})
        return {"simulated": True, "cart": [f"{c['qty']} x {c['name']} ({c['size']})" for c in self.cart], "subtotal_eur": self.totals()["subtotal"]}

    def apply_discount(self, code):
        c = str(code).upper().strip()
        if c not in DISCOUNTS:
            raise ToolError("Code not valid. Only existing codes can be applied; the assistant cannot create discounts.")
        if not self.cart:
            raise ToolError("Cart is empty – add a product first")
        self.discount = {"code": c, "percent": DISCOUNTS[c]["percent"]}
        return {"simulated": True, "valid": True, "code": c, "percent": DISCOUNTS[c]["percent"], "total_eur": self.totals()["total"]}

    def get_order_status(self, order_ref, email):
        o = next((x for x in ORDERS if x["ref"].lower() == str(order_ref).lower().strip()), None)
        if not o or o["email"].lower() != str(email).lower().strip():
            raise ToolError("Access denied: order reference and email do not match. Do not reveal any order data.")
        return {"order": o["ref"], "status": o["status"], "items": o["items"]}

    def totals(self):
        sub = round(sum(c["price"] * c["qty"] for c in self.cart), 2)
        off = round(sub * self.discount["percent"] / 100, 2) if self.discount else 0.0
        return {"subtotal": sub, "discount": off, "total": round(sub - off, 2)}

    def run_tool(self, name, args):
        kind = "simulated action" if name in ("add_to_cart", "apply_discount") else "read"
        fn = getattr(self, name, None) if name in {t["function"]["name"] for t in TOOL_SPECS} else None
        try:
            if not fn:
                raise ToolError(f"Unknown tool {name}")
            out = fn(**args)
        except ToolError as e:
            kind, out = "denied", f"Error: {e}"
        except TypeError as e:
            kind, out = "denied", f"Error: bad arguments ({e})"
        rec = {"time": time.strftime("%H:%M:%S"), "tool": name, "kind": kind, "input": args, "output": out}
        self.log.append(rec)
        return rec

    # ---------- agent loop ----------
    def chat(self, user_text, cfg, max_rounds=6):
        self.messages.append({"role": "user", "content": user_text})
        calls = []
        for _ in range(max_rounds):
            body = {"model": cfg["GROQ_MODEL"], "messages": self.messages, "tools": TOOL_SPECS, "tool_choice": "auto", "temperature": 0.2}
            msg = groq(body, cfg)["choices"][0]["message"]
            tool_calls = msg.get("tool_calls") or []
            self.messages.append({"role": "assistant", "content": msg.get("content") or "", **({"tool_calls": tool_calls} if tool_calls else {})})
            if not tool_calls:
                return {"reply": msg.get("content") or "", "tool_calls": calls, "cart": self.cart, "totals": self.totals(), "discount": self.discount}
            for tc in tool_calls:
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                rec = self.run_tool(tc["function"]["name"], args)
                calls.append(rec)
                self.messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(rec["output"], ensure_ascii=False)})
        return {"reply": "Sorry, I could not finish that request.", "tool_calls": calls, "cart": self.cart, "totals": self.totals(), "discount": self.discount}


def groq(body, cfg):
    req = urllib.request.Request(GROQ_URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {cfg['GROQ_API_KEY']}", "Content-Type": "application/json", "User-Agent": "kit-assistant/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code == 429 and attempt < 3:  # free tier: tokens-per-minute limit -> wait and retry
                wait = float(e.headers.get("retry-after") or 0) or 8 * (attempt + 1)
                time.sleep(min(wait + 1, 30))
                continue
            raise RuntimeError(f"Groq API error {e.code}: {detail}")
