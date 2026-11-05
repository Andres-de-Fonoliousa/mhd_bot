from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_admin_panel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 الطلبات المعلقة", callback_data="adm_pending_orders")
    builder.button(text="📋 جميع الطلبات", callback_data="adm_all_orders")
    builder.button(text="💰 طلبات ايداع الرصيد المعلقة", callback_data="adm_pending_deposits")
    builder.button(text="💵 جميع طلبات ايداع الرصيد", callback_data="adm_all_deposits")
    builder.button(text="💲 إدارة الأسعار", callback_data="adm_manage_prices")
    builder.button(text="💱 سعر الصرف", callback_data="adm_exchange_rate")
    builder.button(text="📊 تقرير الأرباح", callback_data="adm_profit_report")
    builder.button(text="⚙️ التحكم بالبوت", callback_data="adm_bot_control")
    builder.button(text="🚪 خروج", callback_data="adm_exit")
    builder.adjust(1)
    return builder.as_markup()

def get_manage_prices_menu() -> InlineKeyboardMarkup:
    """قائمة اختيار الفئة لتعديل نسبة ربحها"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 تعديل نسبة فري فاير", callback_data="set_profit_ff_gems")
    builder.button(text="💵 تعديل نسبة ببجي UC", callback_data="set_profit_pubg_uc")
    builder.button(text="🎖️ تعديل نسبة العضويات", callback_data="set_profit_ff_subs")
    builder.button(text="🔙 عودة للوحة الأدمن", callback_data="back_to_admin")
    builder.adjust(1)
    return builder.as_markup()

def get_bot_control_menu(current_status: str) -> InlineKeyboardMarkup:
    """لوحة التحكم بالبوت المطابقة للصورة"""
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ تشغيل البوت", callback_data="bot_status_on")
    builder.button(text="⏸️ إيقاف البوت", callback_data="bot_status_off")
    builder.button(text="📢 إذاعة", callback_data="adm_broadcast")
    builder.button(text="🔙 عودة للوحة الأدمن", callback_data="back_to_admin")
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def get_deposit_action_buttons(deposit_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="تأكيد الإيداع ✅️", callback_data=f"confirm_dep_{deposit_id}")
    builder.button(text="رفض الإيداع ❌️", callback_data=f"reject_dep_{deposit_id}")
    builder.adjust(2)
    return builder.as_markup()