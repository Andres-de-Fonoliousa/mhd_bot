import asyncio
import sqlite3
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.core.database import add_or_update_user, get_user_balance, deduct_user_balance, create_deposit, DB_PATH
from bot.config import ADMIN_ID
from bot.bot_instance import get_bot
from bot.core.services.product_service import ProductService
from bot.core.services.order_service import OrderService
from bot.core.services.api_client import MHDAPIError, InsufficientBalanceError, DuplicateOrderError
from bot.keyboards.inline_buttons import (
    get_main_menu, get_back_button, get_retry_kb, get_product_list, get_order_confirm_kb,
    get_profile_kb, get_deposit_methods_kb, get_deposit_confirm_kb,
    get_social_platforms_menu, get_instagram_servers_menu,
)

router = Router()

# ─── Admin alert helper ───────────────────────────────────────────────────────

async def _notify_admin_order_failure(uid, product_name, player_id, qty, total, error_type, error_detail=""):
    try:
        bot = get_bot()
        error_labels = {
            "insufficient_api_balance": "⚠️ رصيد المزود غير كافٍ",
            "duplicate": "⚠️ طلب مكرر",
            "network_error": "🌐 خطأ اتصال بالمزود",
            "api_error": "❌ رفض المزود",
            "unknown": "❓ خطأ غير متوقع",
        }
        label = error_labels.get(error_type, f"❓ {error_type}")
        msg = (
            f"🚨  **فشل طلب**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤  مستخدم:  `{uid}`\n"
            f"🛒  منتج:  {product_name}\n"
            f"🆔  حساب:  `{player_id}`  |  {int(qty)}×\n"
            f"💰  المبلغ:  **{total:,} ل.س**\n"
            f"❌  السبب:  {label}\n"
            + (f"📄  التفاصيل:  {error_detail}" if error_detail else "")
        )
        await bot.send_message(ADMIN_ID, msg)
    except Exception:
        pass

# ─── FSM States ──────────────────────────────────────────────────────────────

class GamingOrder(StatesGroup):
    waiting_for_qty = State()
    waiting_for_player_id = State()

class DepositOrder(StatesGroup):
    waiting_for_amount = State()
    waiting_for_method = State()
    waiting_for_transaction_id = State()


# ═══════════════════════════════════════════════════════════════════════════════
#  START
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    add_or_update_user(uid, message.from_user.username, message.from_user.first_name)
    await message.answer(
        f"👋  أهلاً بك {message.from_user.first_name}  في **FAJR STORE** 🛍️\n\n"
        "أفضل متجر لشحن الألعاب والخدمات الرقمية — اختر القسم المطلوب 👇",
        reply_markup=get_main_menu(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "back_to_main")
async def back_to_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "🏠  القائمة الرئيسية — اختر القسم 👇",
        reply_markup=get_main_menu(),
    )
    await call.answer()


# ═══════════════════════════════════════════════════════════════════════════════
#  CATEGORIES → PRODUCT LIST
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_META = {
    "cat_ff_gems": {
        "title": "💎  جواهر فري فاير",
        "back": "back_to_main",
    },
    "cat_pubg_uc": {
        "title": "💵  شدات ببجي",
        "back": "back_to_main",
    },
    "cat_ff_subs": {
        "title": "🎖️  عضويات وحزم ترقية",
        "back": "back_to_main",
    },
}

@router.callback_query(F.data.in_(CATEGORY_META))
async def show_category_products(call: CallbackQuery):
    cat = call.data
    meta = CATEGORY_META[cat]
    srv = ProductService()
    products = srv.get_services_by_category(cat)

    if not products:
        await call.message.edit_text(
            f"{meta['title']}\n\n"
            "⚠️  لا توجد منتجات متاحة حالياً.\n"
            "يرجى المحاولة لاحقاً بعد مزامنة الأسعار.",
            reply_markup=get_back_button(meta["back"]),
        )
        await call.answer()
        return

    MAX_DISPLAY = 50
    show_products = products[:MAX_DISPLAY]
    total = len(products)

    lines = [f"── {meta['title']} ──", ""]
    for p in show_products:
        lines.append(f"• {p['name']}  —  **{p['price']:,.0f} ل.س**")
    if total > MAX_DISPLAY:
        lines.append(f"\n...و {total - MAX_DISPLAY} منتج آخر")
    lines.append("")
    lines.append("اختر الحزمة المناسبة لك 👇")

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=get_product_list(show_products, meta["back"]),
    )
    await call.answer()


# ═══════════════════════════════════════════════════════════════════════════════
#  PRODUCT SELECTED → GAMING ORDER FLOW
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("prod_"))
async def product_selected(call: CallbackQuery, state: FSMContext):
    service_id = call.data[5:]
    srv = ProductService()
    prod = srv.get_service_by_id(service_id)

    if not prod:
        await call.answer("❌  هذا المنتج غير متاح حالياً.", show_alert=True)
        return

    api_id = prod.get("api_service_id") or prod["service_id"]
    await state.update_data(
        service_id=prod["service_id"],
        api_product_id=api_id,
        product_name=prod["name"],
        category=prod["category"],
        price=prod["price"],
        original_price=prod["original_price"],
        min_qty=prod.get("min_qty", 1),
        max_qty=prod.get("max_qty", 1),
        qty=1,
    )

    min_q = prod.get("min_qty", 1)
    max_q = prod.get("max_qty", 1)
    is_single = (min_q == max_q == 1)

    if is_single:
        text = (
            f"🛒  **{prod['name']}**\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💰  السعر:  **{prod['price']:,.0f} ل.س**\n\n"
            f"📝  أرسل **رقم اللاعب (ID)** الآن:\n"
            f"(مثال: `123456789`)"
        )
        await call.message.edit_text(text, reply_markup=get_back_button("back_to_main"))
        await state.set_state(GamingOrder.waiting_for_player_id)
    else:
        qty_label = f"{int(min_q)}" if min_q == int(min_q) else str(min_q)
        text = (
            f"🛒  **{prod['name']}**\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💰  السعر:  **{prod['price']:,.0f} ل.س**\n\n"
            f"📝  أرسل **الكمية** المطلوبة:\n"
            f"(الحد الأدنى: {qty_label})"
        )
        await call.message.edit_text(text, reply_markup=get_back_button("back_to_main"))
        await state.set_state(GamingOrder.waiting_for_qty)

    await call.answer()


@router.message(GamingOrder.waiting_for_qty)
async def gaming_get_qty(message: Message, state: FSMContext):
    if not message.text.replace(".", "", 1).isdigit():
        await message.answer("❌  يرجى إرسال رقم صحيح للكمية:")
        return

    qty = float(message.text)
    data = await state.get_data()
    min_q = data.get("min_qty", 1)
    max_q = data.get("max_qty", 1)

    if qty < min_q or qty > max_q:
        await message.answer(f"❌  الكمية خارج النطاق ({int(min_q)} – {int(max_q)}). أعد الإرسال:")
        return

    await state.update_data(qty=qty)
    await message.answer(
        f"📝  أرسل **رقم اللاعب (ID)** الآن:\n(مثال: `123456789`)",
        reply_markup=get_back_button("back_to_main"),
    )
    await state.set_state(GamingOrder.waiting_for_player_id)


@router.message(GamingOrder.waiting_for_player_id)
async def gaming_get_player_id(message: Message, state: FSMContext):
    pid = message.text.strip()
    if not pid.isdigit() or len(pid) < 4:
        await message.answer("❌  يرجى إرسال رقم ID صحيح (أرقام فقط، 4 خانات على الأقل):")
        return

    data = await state.get_data()
    await state.update_data(player_id=pid)

    price = data["price"]
    qty = data.get("qty", 1)
    total = int(price * qty)

    text = (
        f"🧾  **إيصال الطلب**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🛒  المنتج:  {data['product_name']}\n"
        f"🔢  الكمية:  {int(qty)}\n"
        f"👤  Player ID:  `{pid}`\n"
        f"💰  السعر:  **{total:,} ل.س**\n\n"
        f"⚠️  تأكد من البيانات قبل التأكيد — الطلبات الخاطئة لا تُسترجع!"
    )
    await state.update_data(total=total)
    await message.answer(
        text,
        reply_markup=get_order_confirm_kb("confirm_game_order", "cancel_game_order"),
    )


# ─── Confirm / Cancel gaming order ───────────────────────────────────────────

@router.callback_query(F.data == "confirm_game_order")
async def confirm_game_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    uid = call.from_user.id
    total = data.get("total", data["price"])

    balance = get_user_balance(uid)
    if balance < total:
        await call.message.edit_text(
            f"❌  **رصيد غير كافٍ**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳  رصيدك الحالي:  **{balance:,.0f} ل.س**\n"
            f"💰  المطلوب:        **{total:,} ل.س**\n\n"
            f"قم بتعبئة رصيدك أولاً.",
            reply_markup=get_back_button("back_to_main"),
        )
        await state.clear()
        await call.answer()
        return

    api_id = data.get("api_product_id", data["service_id"])
    player_id = data["player_id"]
    qty = data.get("qty", 1)
    product_name = data["product_name"]

    result = None
    error_type = None
    error_msg = None

    try:
        order_svc = OrderService()
        result = await order_svc.create_order(
            api_product_id=api_id,
            qty=qty,
            player_id=player_id,
            chat_id=uid,
            product_name=product_name,
        )
        deduct_user_balance(uid, total)

        # إشعار الأدمن بالنجاح
        bot = get_bot()
        await bot.send_message(
            ADMIN_ID,
            f"✅  **طلب جديد ناجح**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤  مستخدم:  `{uid}`\n"
            f"🛒  منتج:  {product_name}\n"
            f"🆔  حساب:  `{player_id}`  |  {int(qty)}×\n"
            f"💰  المبلغ:  **{total:,} ل.س**"
        )
    except InsufficientBalanceError:
        error_type = "insufficient_api_balance"
    except DuplicateOrderError as e:
        error_type = "duplicate"
        error_msg = str(e)
    except MHDAPIError as e:
        error_type = "api_error"
        error_msg = str(e)
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        error_type = "network_error"
        error_msg = str(e)
    except Exception as e:
        error_type = "unknown"
        error_msg = str(e)

    if not result:
        await _notify_admin_order_failure(
            uid=uid,
            product_name=product_name,
            player_id=player_id,
            qty=qty,
            total=total,
            error_type=error_type,
            error_detail=str(error_msg or ""),
        )

    if result:
        await state.clear()
        await call.message.edit_text(
            f"✅  **تم تأكيد الطلب بنجاح!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🛒  {product_name}\n"
            f"👤  Player ID:  `{player_id}`\n"
            f"🔢  الكمية:  {int(qty)}\n"
            f"💰  المخصوم:  **{total:,} ل.س**\n\n"
            f"تابع حالة الطلب من قائمة **حسابي**.",
            reply_markup=get_back_button("back_to_main"),
        )
        await call.answer()
        return

    # Order failed — don't clear state if retry is possible
    if error_type == "insufficient_api_balance":
        await state.clear()
        text = (
            f"⚠️  **خطأ من المزود**\n━━━━━━━━━━━━━━━━━━\n"
            f"🛒  {product_name}\n👤  Player ID:  `{player_id}`\n\n"
            f"❌  رصيد المزود غير كافٍ حاليًا.\n"
            f"لم يتم خصم أي مبلغ من رصيدك.\n\nيرجى المحاولة لاحقاً."
        )
        reply_markup = get_back_button("back_to_main")
    elif error_type == "duplicate":
        text = (
            f"⚠️  **طلب مكرر**\n━━━━━━━━━━━━━━━━━━\n"
            f"🛒  {product_name}\n👤  Player ID:  `{player_id}`\n\n"
            f"لم يتم خصم أي مبلغ من رصيدك."
        )
        reply_markup = get_retry_kb("confirm_game_order")
    elif error_type == "network_error":
        text = (
            f"⚠️  **خطأ في الاتصال**\n━━━━━━━━━━━━━━━━━━\n"
            f"🛒  {product_name}\n👤  Player ID:  `{player_id}`\n\n"
            f"❌  تعذر الاتصال بخادم المزود.\n"
            f"لم يتم خصم أي مبلغ من رصيدك.\n\nالرجاء المحاولة مرة أخرى."
        )
        reply_markup = get_retry_kb("confirm_game_order")
    elif error_type == "api_error":
        await state.clear()
        text = (
            f"⚠️  **خطأ من المزود**\n━━━━━━━━━━━━━━━━━━\n"
            f"🛒  {product_name}\n👤  Player ID:  `{player_id}`\n\n"
            f"❌  {error_msg}\n"
            f"لم يتم خصم أي مبلغ من رصيدك.\n\nيرجى المحاولة لاحقاً."
        )
        reply_markup = get_back_button("back_to_main")
    else:
        text = (
            f"⚠️  **حدث خطأ غير متوقع**\n━━━━━━━━━━━━━━━━━━\n"
            f"🛒  {product_name}\n👤  Player ID:  `{player_id}`\n\n"
            f"لم يتم خصم أي مبلغ من رصيدك.\n\nيمكنك المحاولة مرة أخرى."
        )
        reply_markup = get_retry_kb("confirm_game_order")

    await call.message.edit_text(text, reply_markup=reply_markup)
    await call.answer()


@router.callback_query(F.data == "cancel_game_order")
async def cancel_game_order(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌  تم إلغاء الطلب.", reply_markup=get_main_menu())
    await call.answer()


# ═══════════════════════════════════════════════════════════════════════════════
#  USER PROFILE
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "user_profile")
async def show_profile(call: CallbackQuery):
    uid = call.from_user.id
    balance = get_user_balance(uid)

    conn = sqlite3.connect(DB_PATH)
    order_count = conn.execute(
        "SELECT COUNT(*) FROM api_orders WHERE chat_id = ?", (uid,)
    ).fetchone()[0]
    conn.close()

    text = (
        f"👤  **حسابي الشخصي**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔  المعرف:  `{uid}`\n"
        f"💰  الرصيد:  **{balance:,.0f} ل.س**\n"
        f"📦  إجمالي الطلبات:  **{order_count}**\n\n"
        f"يمكنك متابعة طلباتك السابقة من الأسفل 👇"
    )
    await call.message.edit_text(text, reply_markup=get_profile_kb())
    await call.answer()


@router.callback_query(F.data == "my_orders")
async def show_my_orders(call: CallbackQuery):
    uid = call.from_user.id

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT product_name, player_id, qty, status FROM api_orders WHERE chat_id = ? ORDER BY id DESC LIMIT 10",
        (uid,)
    ).fetchall()
    conn.close()

    if not rows:
        await call.message.edit_text(
            "📋  **لا توجد طلبات سابقة.**\n\nقم بطلب منتج من القائمة الرئيسية.",
            reply_markup=get_back_button("back_to_main"),
        )
        await call.answer()
        return

    status_map = {
        "accept":     ("✅", "مكتمل"),
        "reject":     ("❌", "مرفوض"),
        "wait":       ("⏳", "قيد التنفيذ"),
        "pending":    ("⏳", "قيد الانتظار"),
        "processing": ("🔄", "جاري التنفيذ"),
        "timeout":    ("⚠️", "منتهي المهلة"),
    }
    lines = ["📋  **طلباتي الأخيرة**\n━━━━━━━━━━━━━━━━━━"]
    for row in rows:
        icon, label = status_map.get(row[3], ("❓", "غير معروف"))
        lines.append(f"{icon}  **{label}**\n   🛒  {row[0]}\n   🆔  {row[1]}  |  {int(row[2])}×")

    await call.message.edit_text(
        "\n\n".join(lines),
        reply_markup=get_back_button("user_profile"),
    )
    await call.answer()


# ═══════════════════════════════════════════════════════════════════════════════
#  SOCIAL SERVICES
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "social_services")
async def social_services(call: CallbackQuery):
    await call.message.edit_text(
        "🌐  **خدمات التواصل الاجتماعي**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "اختر المنصة المطلوبة 👇",
        reply_markup=get_social_platforms_menu(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("platform_"))
async def social_platform_selected(call: CallbackQuery):
    platform = call.data.replace("platform_", "")
    if platform == "facebook":
        await call.message.edit_text(
            "🔵  **خدمات فيسبوك**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "قيد الإعداد — سيتم توفير الخدمات قريباً.",
            reply_markup=get_back_button("social_services"),
        )
    elif platform == "instagram":
        await call.message.edit_text(
            "🟣  **خدمات انستغرام**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "اختر نوع السيرفر 👇",
            reply_markup=get_instagram_servers_menu(),
        )
    await call.answer()


@router.callback_query(F.data.startswith("insta_server_"))
async def instagram_server_selected(call: CallbackQuery):
    server = call.data.replace("insta_server_", "")
    await call.message.edit_text(
        f"⚡  سيرفر انستغرام ({'فوري' if server == 'fast' else 'يدوي'})\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "قيد الإعداد — سيتم توفير الخدمات قريباً.",
        reply_markup=get_back_button("social_services"),
    )
    await call.answer()


# ═══════════════════════════════════════════════════════════════════════════════
#  SUPPORT
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "support_info")
async def show_support(call: CallbackQuery):
    await call.message.edit_text(
        "📞  **الدعم الفني**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "للتواصل مع الإدارة عبر المعرف التالي:\n\n"
        "👤  @fajramouri\n\n"
        "ساعات العمل:  على مدار الساعة 🕐",
        reply_markup=get_back_button("back_to_main"),
    )
    await call.answer()


# ═══════════════════════════════════════════════════════════════════════════════
#  DEPOSIT
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "deposit_start")
async def deposit_start(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "💰  **تعبئة رصيد**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "أرسل **المبلغ** الذي تريد إيداعه بالليرة السورية:\n"
        "(مثال: `50000`)",
        reply_markup=get_back_button("back_to_main"),
    )
    await state.set_state(DepositOrder.waiting_for_amount)
    await call.answer()


@router.message(DepositOrder.waiting_for_amount)
async def deposit_get_amount(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("❌  يرجى إرسال مبلغ صحيح (أرقام فقط):")
        return
    amount = int(message.text)
    await state.update_data(amount=amount)
    await message.answer(
        f"💳  **اختر وسيلة الدفع**\nالمبلغ: **{amount:,} ل.س**\n\nاختر الطريقة المناسبة 👇",
        reply_markup=get_deposit_methods_kb(),
    )
    await state.set_state(DepositOrder.waiting_for_method)


@router.callback_query(DepositOrder.waiting_for_method, F.data.startswith("dep_meth_"))
async def deposit_get_method(call: CallbackQuery, state: FSMContext):
    method_map = {
        "dep_meth_wallet": "📱 محفظة إلكترونية",
        "dep_meth_bank":   "🏦 تحويل بنكي",
        "dep_meth_card":   "💳 بطاقة ائتمان",
    }
    method = method_map.get(call.data, "أخرى")
    await state.update_data(payment_method=method)
    data = await state.get_data()
    await call.message.edit_text(
        f"📝  **تفاصيل الإيداع**\n━━━━━━━━━━━━━━━━━━\n"
        f"💰  المبلغ:  **{data['amount']:,} ل.س**\n"
        f"💳  الوسيلة:  {method}\n\n"
        f"أرسل **رقم العملية أو الإشارة**:",
        reply_markup=get_back_button("back_to_main"),
    )
    await state.set_state(DepositOrder.waiting_for_transaction_id)
    await call.answer()


@router.message(DepositOrder.waiting_for_transaction_id)
async def deposit_get_transaction(message: Message, state: FSMContext):
    tx = message.text.strip()
    if not tx:
        await message.answer("❌  يرجى إرسال رقم العملية:")
        return

    data = await state.get_data()
    uid = message.from_user.id
    name = message.from_user.first_name or "Unknown"

    dep_id = create_deposit(
        chat_id=uid,
        first_name=name,
        amount=data["amount"],
        payment_method=data["payment_method"],
        transaction_id=tx,
    )

    await message.answer(
        f"✅  **تم إرسال طلب الإيداع بنجاح!**\n━━━━━━━━━━━━━━━━━━\n"
        f"💰  المبلغ:  **{data['amount']:,} ل.س**\n"
        f"💳  الوسيلة:  {data['payment_method']}\n"
        f"🔖  رقم الطلب:  `#{dep_id}`\n\n"
        f"📌  سيتم مراجعة الطلب وإضافة الرصيد بعد التأكيد.",
        reply_markup=get_back_button("back_to_main"),
    )

    bot = get_bot()
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💰  **طلب إيداع جديد**\n━━━━━━━━━━━━━━━━━━\n"
            f"🆔  رقم الطلب:  `#{dep_id}`\n"
            f"👤  المستخدم:  {name} (ID: `{uid}`)\n"
            f"💰  المبلغ:  **{data['amount']:,} ل.س**\n"
            f"💳  الوسيلة:  {data['payment_method']}\n"
            f"🔖  العملية:  `{tx}`\n\n"
            f"استخدم لوحة التحكم للموافقة أو الرفض.",
        )
    except Exception:
        pass

    await state.clear()


@router.callback_query(F.data == "dep_cancel")
async def deposit_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌  تم إلغاء طلب الإيداع.", reply_markup=get_main_menu())
    await call.answer()