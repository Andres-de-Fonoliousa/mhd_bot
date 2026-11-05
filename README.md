# MHD Bot — Channel-Gated Telegram Store

An [aiogram 3](https://aiogram.dev) Telegram store bot for the Arabic market (Syrian lible pricing, Arabic UI): game top-ups (Free Fire gems, PUBG UC, memberships) and social-media services, with catalog and order fulfillment synced from an MHD provider API. Users must join your Telegram channel before they can use the bot.

## Features

- **Channel gating** — middleware checks channel membership on every message/callback; non-members get a subscribe prompt (Arabic).
- **Catalog from MHD provider sync** — products/prices sync from the provider API on startup and every 6 hours; per-category profit margins on top of source prices.
- **User purchase flow** — category → product → quantity → player ID → confirm; orders go straight to the provider API. Arabic FSM flow with retry/cancel states.
- **Wallet & deposits** — SYP/USD balances, manual deposit submission (amount → method → transaction ID) with admin approval/rejection.
- **Admin panel** (`/admin`) — pending/all deposits, pending/all orders, broadcast, exchange rate (SYP per USD), per-category profit margins, bot on/off, profit report.
- **Failure alerts** — provider errors (insufficient balance, duplicates, network) are reported to the admin chat instantly.
- **SQLite storage** — users, orders, deposits, settings; `seed.py` bootstraps the schema from `products.json`.

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements.txt

copy .env.example .env        # then fill in your values
python seed.py                # create database + seed catalog
python main.py                # start the bot
```

`.env` (gitignored — real secrets live here):

```env
BOT_TOKEN=your_bot_token_here
ADMIN_ID=123456789
CHANNEL_USERNAME=@your_channel

API_BASE_URL=https://your-api.com/api
API_TOKEN=your_api_token_here

USD_TO_LIRA_RATE=135
PROFIT_MARGIN_FF_GEMS=1.02
PROFIT_MARGIN_PUBG_UC=1.02
PROFIT_MARGIN_FF_SUBS=1.02
```

## Project layout

```
main.py                      entry: sync, routers, middleware, polling
bot/config.py                env-driven settings (python-dotenv)
bot/bot_instance.py          Bot/Dispatcher singleton
bot/middleware/subscription.py  channel-gating middleware
bot/handlers/user_handler.py    purchase + deposit + profile flow
bot/handlers/admin_handler.py   admin panel
bot/keyboards/                  inline keyboards
bot/core/database.py            SQLite layer
bot/core/services/              MHD API client, product/order/sync services
products.json                   seed catalog (plain data)
seed.py                         schema + seed script
```

## ملخص بالعربية

بوت متجر تيليجرام (aiogram 3) للسوق العربي: شحن ألعاب (جواهر فري فاير، شدات ببجي، عضويات) وخدمات سوشيال ميديا، مع مزامنة تلقائية للمنتجات والأسعار من مزود MHD كل 6 ساعات. لا يستخدم البوت إلا بعد الاشتراك بقناتك (بوابة اشتراك إلزامية). يتضمن تدفق شراء كامل بالعربية، محفظة بالليرة السورية والدولار، إيداعات بموافقة إدارية، ولوحة إدارة (طلبات، إيداعات، بث، أسعار الصرف، هوامش الربح، تشغيل/إيقاف البوت).

## License

[MIT](LICENSE) © 2026 Andres-de-Fonoliousa
