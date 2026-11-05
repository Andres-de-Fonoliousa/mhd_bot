import sqlite3
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.keyboards.inline_buttons import get_back_button
from bot.config import ADMIN_ID
from bot.core.database import get_setting_value, update_setting_value, get_deposits, approve_deposit, reject_deposit, DB_PATH
from bot.keyboards.admin_keyboards import (
    get_admin_panel, get_deposit_action_buttons, get_manage_prices_menu, get_bot_control_menu
)
from bot.bot_instance import get_bot

router = Router()

class AdminStates(StatesGroup):
    waiting_for_profit_rate = State()
    waiting_for_exchange_rate = State()
    waiting_for_broadcast_msg = State()

@router.message(Command("admin"))
async def open_admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Admin panel\nChoose an action:", reply_markup=get_admin_panel())

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.edit_text("Admin panel\nChoose an action:", reply_markup=get_admin_panel())
    await callback.answer()

@router.callback_query(F.data == "adm_manage_prices")
async def manage_prices(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.edit_text("Manage profit margins\nChoose category:", reply_markup=get_manage_prices_menu())
    await callback.answer()

@router.callback_query(F.data.startswith("set_profit_"))
async def ask_for_profit_rate(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    category_key = callback.data.replace("set_profit_", "")
    await state.update_data(current_cat=category_key)

    current_margin = float(get_setting_value(category_key) or 1.02)
    current_percentage = round((current_margin - 1) * 100)

    await callback.message.answer(f"Current margin: {current_percentage}%\nSend new percentage (e.g. 5 for 5%):")
    await state.set_state(AdminStates.waiting_for_profit_rate)
    await callback.answer()

@router.message(AdminStates.waiting_for_profit_rate)
async def save_profit_rate(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    if not message.text.isdigit():
        await message.answer("Please enter a valid number.")
        return

    user_data = await state.get_data()
    cat_key = user_data['current_cat']
    input_percent = int(message.text)
    new_margin = 1 + (input_percent / 100)

    update_setting_value(cat_key, str(new_margin))
    await state.clear()
    await message.answer(f"Profit margin updated to {input_percent}%")

@router.callback_query(F.data == "adm_exchange_rate")
async def ask_exchange_rate(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    current_rate = get_setting_value("exchange_rate")
    await callback.message.answer(
        f"Send new exchange rate (integer: SYP per 1 USD):\nCurrent: {current_rate}"
    )
    await state.set_state(AdminStates.waiting_for_exchange_rate)
    await callback.answer()

@router.message(AdminStates.waiting_for_exchange_rate)
async def save_exchange_rate(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    if not message.text.isdigit():
        await message.answer("Please enter a valid number.")
        return

    update_setting_value("exchange_rate", message.text)
    await state.clear()
    await message.answer(f"Exchange rate updated to {message.text} SYP per 1 USD.")

@router.callback_query(F.data == "adm_profit_report")
async def show_profit_report(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    report_msg = (
        "Weekly Profit Report\n"
        "Period: 22-06-2026 -> 28-06-2026\n"
        "_________________________\n\n"
        "Total Sales: 0 SYP\n"
        "Total Cost: 0 SYP\n"
        "Net Profit: 0 SYP"
    )
    await callback.message.answer(report_msg)
    await callback.answer()

@router.callback_query(F.data == "adm_pending_orders")
async def adm_pending_orders(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    from bot.core.services.order_service import OrderService
    svc = OrderService()
    orders = svc.get_all_orders(limit=30, status=("wait", "pending"))
    if not orders:
        await call.message.edit_text(
            "📭  **لا توجد طلبات معلقة.**",
            reply_markup=get_back_button("back_to_admin"),
        )
        await call.answer()
        return
    lines = ["📦  **الطلبات المعلقة**\n━━━━━━━━━━━━━━━━━━"]
    for o in orders:
        lines.append(
            f"🛒  {o['product_name'] or '—'}\n"
            f"   👤  حساب:  {o['player_id']}  |  {int(o['qty'])}×\n"
            f"   🆔  مستخدم:  `{o['chat_id']}`\n"
            f"   📅  {o['created_at'][:16]}"
        )
    await call.message.edit_text(
        "\n\n".join(lines)[:4000],
        reply_markup=get_back_button("back_to_admin"),
    )
    await call.answer()

@router.callback_query(F.data == "adm_all_orders")
async def adm_all_orders(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    from bot.core.services.order_service import OrderService
    svc = OrderService()
    orders = svc.get_all_orders(limit=30)
    if not orders:
        await call.message.edit_text(
            "📭  **لا توجد طلبات حتى الآن.**",
            reply_markup=get_back_button("back_to_admin"),
        )
        await call.answer()
        return
    lines = ["📋  **جميع الطلبات (آخر 30)**\n━━━━━━━━━━━━━━━━━━"]
    status_labels = {
        "pending": "⏳  قيد الانتظار",
        "wait":    "⏳  قيد التنفيذ",
        "accept":  "✅  مكتمل",
        "reject":  "❌  مرفوض",
        "unknown": "❓  غير معروف",
        "timeout": "⏰  انتهت المهلة",
    }
    for o in orders:
        label = status_labels.get(o["status"], f"❓  {o['status']}")
        err = o.get("error_reason", "")
        err_line = f"\n   ⚠️  {err}" if err else ""
        lines.append(
            f"{label}\n"
            f"   🛒  {o['product_name'] or '—'}\n"
            f"   👤  {o['player_id']}  |  {int(o['qty'])}×\n"
            f"   👤  مستخدم:  `{o['chat_id']}`  |  {o['created_at'][:16]}"
            f"{err_line}"
        )
    await call.message.edit_text(
        "\n\n".join(lines)[:4000],
        reply_markup=get_back_button("back_to_admin"),
    )
    await call.answer()

@router.callback_query(F.data == "adm_bot_control")
async def bot_control_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    status = get_setting_value("bot_status")
    status_text = "Active" if status == "on" else "Paused"
    await callback.message.edit_text(
        f"Bot Control\n\nStatus: {status_text}\nChoose action:",
        reply_markup=get_bot_control_menu(status)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("bot_status_"))
async def change_bot_status(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    new_status = callback.data.replace("bot_status_", "")
    update_setting_value("bot_status", new_status)

    status_text = "Active" if new_status == "on" else "Paused"
    await callback.message.edit_text(
        f"Bot Control\n\nStatus: {status_text}\nChoose action:",
        reply_markup=get_bot_control_menu(new_status)
    )
    await callback.answer()

@router.callback_query(F.data == "adm_broadcast")
async def ask_broadcast_msg(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("Send the message to broadcast to all users:")
    await state.set_state(AdminStates.waiting_for_broadcast_msg)
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast_msg)
async def trigger_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    broadcast_text = message.text
    await state.clear()

    from bot.core.database import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM users")
    users = cursor.fetchall()
    conn.close()

    success_count = 0
    bot = get_bot()

    await message.answer("Broadcasting...")
    for user in users:
        try:
            await bot.send_message(user[0], broadcast_text)
            success_count += 1
        except Exception:
            continue

    await message.answer(f"Broadcast complete! Sent to {success_count} users.")


@router.callback_query(F.data == "adm_exit")
async def admin_exit(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    await call.message.delete()
    await call.answer()


# ═══════════════════════════════════════════════════════════════════════════════
#  DEPOSIT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm_pending_deposits")
async def show_pending_deposits(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    deposits = get_deposits(status="pending")
    if not deposits:
        await call.message.edit_text(
            "📭  **لا توجد طلبات إيداع معلقة.**",
            reply_markup=get_back_button("back_to_admin"),
        )
        await call.answer()
        return

    lines = ["💰  **طلبات الإيداع المعلقة**\n━━━━━━━━━━━━━━━━━━"]
    for d in deposits:
        lines.append(
            f"`#{d['id']}`  |  {d['first_name']}  |  **{d['amount']:,.0f} ل.س**\n"
            f"   {d['payment_method']}  |  {d['created_at'][:16]}"
        )
    lines.append("\nاختر رقم الطلب للمراجعة 👇")

    b = InlineKeyboardBuilder()
    for d in deposits:
        b.button(text=f"#{d['id']}  {d['first_name']}  {d['amount']:,.0f} ل.س", callback_data=f"adm_review_dep_{d['id']}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="🔙  عودة", callback_data="back_to_admin"))

    await call.message.edit_text("\n".join(lines), reply_markup=b.as_markup())
    await call.answer()


@router.callback_query(F.data == "adm_all_deposits")
async def show_all_deposits(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    deposits = get_deposits(limit=20)
    if not deposits:
        await call.message.edit_text(
            "📭  **لا توجد طلبات إيداع.**",
            reply_markup=get_back_button("back_to_admin"),
        )
        await call.answer()
        return

    lines = ["💵  **جميع طلبات الإيداع (آخر 20)**\n━━━━━━━━━━━━━━━━━━"]
    for d in deposits:
        status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(d["status"], "❓")
        lines.append(
            f"{status_icon} `#{d['id']}`  {d['first_name']}  **{d['amount']:,.0f} ل.س**\n"
            f"   {d['payment_method']}  |  {d['status']}  |  {d['created_at'][:10]}"
        )
    lines.append("\n🔙  استخدم زر الرجوع")

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=get_back_button("back_to_admin"),
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_review_dep_"))
async def review_deposit(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    dep_id = int(call.data.replace("adm_review_dep_", ""))
    deposits = get_deposits(status="pending")
    dep = next((d for d in deposits if d["id"] == dep_id), None)
    if not dep:
        await call.answer("⚠️  لم يعد هذا الطلب معلقاً.", show_alert=True)
        return

    text = (
        f"🧾  **مراجعة طلب إيداع**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔖  رقم الطلب:  `#{dep['id']}`\n"
        f"👤  المستخدم:  {dep['first_name']} (ID: `{dep['chat_id']}`)\n"
        f"💰  المبلغ:  **{dep['amount']:,.0f} ل.س**\n"
        f"💳  الوسيلة:  {dep['payment_method']}\n"
        f"🔖  العملية:  `{dep['transaction_id'] or '—'}`\n"
        f"📅  التاريخ:  {dep['created_at']}\n\n"
        f"هل تريد تأكيد الإيداع أم رفضه؟"
    )
    await call.message.edit_text(text, reply_markup=get_deposit_action_buttons(dep["id"]))
    await call.answer()


@router.callback_query(F.data.startswith("confirm_dep_"))
async def confirm_deposit(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    dep_id = int(call.data.replace("confirm_dep_", ""))
    chat_id = approve_deposit(dep_id)

    if not chat_id:
        await call.answer("⚠️  لم يتم العثور على الطلب أو تمت معالجته مسبقاً.", show_alert=True)
        return

    await call.message.edit_text(
        f"✅  **تم تأكيد الإيداع `#{dep_id}` بنجاح!**\n"
        f"تم إضافة الرصيد إلى المستخدم.",
        reply_markup=get_back_button("back_to_admin"),
    )
    await call.answer()

    bot = get_bot()
    try:
        await bot.send_message(
            chat_id,
            f"✅  **تم تأكيد طلب الإيداع!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔖  رقم الطلب:  `#{dep_id}`\n"
            f"💰  تم إضافة الرصيد إلى حسابك بنجاح.\n"
            f"شكراً لثقتك 🌿",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("reject_dep_"))
async def reject_deposit(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    dep_id = int(call.data.replace("reject_dep_", ""))
    chat_id = reject_deposit(dep_id)

    if not chat_id:
        await call.answer("⚠️  لم يتم العثور على الطلب أو تمت معالجته مسبقاً.", show_alert=True)
        return

    await call.message.edit_text(
        f"❌  **تم رفض الإيداع `#{dep_id}`.**",
        reply_markup=get_back_button("back_to_admin"),
    )
    await call.answer()

    bot = get_bot()
    try:
        await bot.send_message(
            chat_id,
            f"❌  **تم رفض طلب الإيداع.**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔖  رقم الطلب:  `#{dep_id}`\n"
            f"يرجى التواصل مع الدعم الفني للمزيد من التفاصيل.",
        )
    except Exception:
        pass
