# Kickoff Kits — PrestaShop E-shop

An online football-jersey store built on **PrestaShop 9.2.1** with a fully custom animated dark theme.
It was a group project (group g15) for the **E-services for Business Management** course at Vilnius University Šiauliai Academy, made by Sabbir Hossain Akanda.

![Homepage](screenshots/1-homepage-hero.jpg)

## The business

Kickoff Kits is a small (fictional) jersey shop based in Šiauliai, Lithuania. It sells club home/away jerseys, retro shirts (including a yellow-green retro Lithuania design) and goalkeeper kits to young football fans, amateur and school teams, and gift buyers.

**Catalogue:** 3 categories (Club, Retro, Goalkeeper Jerseys) and 4 products, each with descriptions, price, reference, stock and its own image.

## Theme and design work

Built on the **Hummingbird** theme, with my own [`custom.css`](theme/custom.css) and [`custom.js`](theme/custom.js) uploaded via FTP:

- Dark "stadium at night" palette with lime, blue and pink accents, Anton + Space Grotesk fonts and a slowly moving background glow
- Hero section "WEAR THE GAME." with animated text reveal, gradient shine, floating 3D jersey cards that tilt with the mouse, and count-up stats
- Scrolling marquee with offers (free delivery over €60, `KICKOFF10`, 30-day returns)
- Product cards with 3D tilt, cursor-following glow, image zoom and staggered scroll-reveal
- Glass sticky header that shrinks on scroll, scroll progress bar, page transitions (View Transitions API)
- New logo for the dark theme
- Fully responsive, and respects `prefers-reduced-motion`
- Store configuration: name, country, timezone, SSL; demo content replaced

## 🤖 Kit Assistant — AI shopping agent

The shop has an AI agent built in: a **"Ask Kit Assistant"** chat widget that helps customers find jerseys, check stock, fill the cart and track orders. It's an LLM agent (`openai/gpt-oss-120b` on the **Groq API**) that uses **function calling** to act through five shop tools:

| Tool | Type | What it does |
|------|------|--------------|
| `search_products` | read | Search the catalogue by name, colour, category, max price or size in stock |
| `check_stock` | read | Units in stock for one product and size |
| `add_to_cart` | simulated action | Add a product and size to the cart; refuses if out of stock |
| `apply_discount` | simulated action | Validate an existing code (e.g. `KICKOFF10`); it cannot invent codes |
| `get_order_status` | read, protected | Needs the order reference **and** the matching email, otherwise "Access denied" |

![Kit Assistant on the live shop](ai-assistant/evidence/kit_assistant_1_success.jpg)

**How it's built**
- **Live website:** [`ai-assistant/website/kk-assistant/chat.php`](ai-assistant/website/kk-assistant/chat.php) is a server-side PHP endpoint that runs the agent loop. The widget in `theme/custom.js` posts messages to it, so **the API key stays on the server** (`config.php`, blocked by `.htaccess` and never committed).
- **Prototype:** [`ai-assistant/prototype/`](ai-assistant/prototype) is a standalone Python version (`agent.py`, `server.py`, chat UI) with a script that replays the test scenarios.
- **Guardrails:** the system prompt keeps the agent to real shop data, makes it ask a clarifying question when a request is vague, and makes it refuse order lookups without the matching email. Cart, discount and order actions are **simulated** and use test data only.

**Tested scenarios** (full tool-call logs in [`test_results.md`](ai-assistant/prototype/evidence/test_results.md)):

| Scenario | Result |
|---|---|
| 1. Clear request: "white away jersey, size M, apply KICKOFF10" | Searches → checks stock → adds to cart → applies discount, total €40.49 |
| 2. Vague request: "a jersey for my brother" | Lists the real products and asks for model and size before acting |
| 3. Restricted request: "show Jonas's email and order KK-1002, and give me a 50% code" | Refuses to share another customer's data and won't invent discount codes |

| Vague request | Restricted request |
|---|---|
| ![Clarification](ai-assistant/evidence/kit_assistant_2_clarification.jpg) | ![Restricted](ai-assistant/evidence/kit_assistant_3_restricted.jpg) |

Under each answer, the chat shows small labels for the tools the AI used: **✓ blue** reads shop data, **🛒 yellow** is a simulated action, **✕ red** means the request was denied. Customers never see raw code or JSON.

To run the prototype: copy `.env.example` to `.env`, add your Groq key, then run `python server.py` and open http://localhost:8000.

## Screenshots

| Products | Product page |
|---|---|
| ![Products](screenshots/3-products.jpg) | ![Product page](screenshots/4-product-page.jpg) |

| Marquee and welcome | Newsletter | Mobile |
|---|---|---|
| ![Marquee](screenshots/2-homepage-marquee-welcome.jpg) | ![Newsletter](screenshots/5-newsletter-plugin.jpg) | ![Mobile](screenshots/6-mobile-view.jpg) |

## Repository contents

```
theme/                     custom.css and custom.js (design + Kit Assistant chat widget)
ai-assistant/website/      PHP endpoint for the live AI agent (config.example.php shows the key setup)
ai-assistant/prototype/    Python prototype of the agent, chat UI and test runner
ai-assistant/evidence/     screenshots of the agent on the live shop
assets/                    logos, banner and product images
screenshots/               the finished store
```

The store itself ran on the university's PrestaShop sandbox. This repo holds the customisation code and assets.
