# Kickoff Kits – Kit Assistant (LLM shopping assistant prototype)

Sabbir Hossain Akanda · E-services for Business Management Algorithms (group g15)

A customer-facing AI assistant for the Kickoff Kits e-shop. A Groq-hosted LLM (`openai/gpt-oss-120b`) uses **function calling** to work with five shop tools. **All data is test data; cart and discount actions are SIMULATED** and never touch the real PrestaShop shop.

| Tool | Type | What it does |
|---|---|---|
| `search_products` | read | Search the catalogue (name, colour, category, max price, size in stock) |
| `check_stock` | read | Units in stock for one product and size |
| `add_to_cart` | simulated action | Add a product/size to the simulated cart (refuses if out of stock) |
| `apply_discount` | simulated action | Validate an existing code (KICKOFF10 = 10%); cannot create codes |
| `get_order_status` | read, protected | Needs order ref **and** matching email; otherwise "Access denied" |

## Run it

Requirements: Python 3.10+ (no extra packages) and a free Groq API key from https://console.groq.com/keys

1. Copy `.env.example` to `.env` and paste your key after `GROQ_API_KEY=`
   (or set a `GROQ_API_KEY` environment variable).
2. Start the app: double-click `run.bat`, or run `python server.py`.
3. Open **http://localhost:8000** and click a test-scenario button or type a message.

Run the three test scenarios from the command line (saves evidence to `evidence/`):

```
python run_scenarios.py
```

## Files

- `agent.py` – test data, the five tools, system prompt and the LLM agent loop (Groq API)
- `server.py` – local web server (`/api/chat`, `/api/reset`, `/api/testdata`)
- `index.html` – chat UI with live tool-call log and simulated cart
- `run_scenarios.py` – runs the 3 required test scenarios and writes `evidence/`
- `evidence/` – screenshots, `tool_call_records.json`, `test_results.md`

The free Groq tier allows about 8,000 tokens per minute; the code waits and retries automatically when the limit is hit.
