from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ─── Main Menu ───────────────────────────────────────────────────────────────

def get_main_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💎  جواهر فري فاير", callback_data="cat_ff_gems")
    b.button(text="💵  شدات ببجي",      callback_data="cat_pubg_uc")
    b.button(text="🎖️  عضويات وحزم ترقية", callback_data="cat_ff_subs")
    b.button(text="🌐  خدمات التواصل",   callback_data="social_services")
    b.button(text="💰  تعبئة رصيد",     callback_data="deposit_start")
    b.button(text="👤  حسابي",           callback_data="user_profile")
    b.button(text="📞  الدعم الفني",     callback_data="support_info")
    b.adjust(2)
    return b.as_markup()


# ─── Generic Navigation ──────────────────────────────────────────────────────

def get_back_button(callback_data: str = "back_to_main", text: str = "🔙  رجوع") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=text, callback_data=callback_data)
    return b.as_markup()


# ─── Product Category Menu (dynamic products from DB) ────────────────────────

def get_product_list(products: list, back_callback: str) -> InlineKeyboardMarkup:
    """Build a menu from a list of product dicts with keys: service_id, name, price (in SYP)."""
    b = InlineKeyboardBuilder()
    for p in products:
        price = int(p['price'])
        label = f"{p['name']}  —  💰 {price:,} ل.س"
        b.button(text=label, callback_data=f"prod_{p['service_id']}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="🔙  رجوع", callback_data=back_callback))
    return b.as_markup()


# ─── Order Confirmation ──────────────────────────────────────────────────────

def get_order_confirm_kb(confirm_cb: str, cancel_cb: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅  تأكيد الطلب", callback_data=confirm_cb)
    b.button(text="❌  إلغاء",       callback_data=cancel_cb)
    b.adjust(2)
    return b.as_markup()


# ─── Profile ─────────────────────────────────────────────────────────────────

def get_profile_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📋  طلباتي السابقة", callback_data="my_orders")
    b.button(text="🔙  رجوع",           callback_data="back_to_main")
    b.adjust(1)
    return b.as_markup()


# ─── Social Media ────────────────────────────────────────────────────────────

def get_social_platforms_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔵  فيسبوك",     callback_data="platform_facebook")
    b.button(text="🟣  انستغرام",   callback_data="platform_instagram")
    b.adjust(2)
    b.row(InlineKeyboardButton(text="🔙  رجوع", callback_data="back_to_main"))
    return b.as_markup()


def get_instagram_servers_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⚡  سيرفر فوري",   callback_data="insta_server_fast")
    b.button(text="⚙️  سيرفر يدوي",   callback_data="insta_server_manual")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="🔙  رجوع", callback_data="social_services"))
    return b.as_markup()


# ─── Deposit ─────────────────────────────────────────────────────────────────

def get_deposit_methods_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📱  محفظة إلكترونية", callback_data="dep_meth_wallet")
    b.button(text="🏦  تحويل بنكي",      callback_data="dep_meth_bank")
    b.button(text="💳  بطاقة ائتمان",    callback_data="dep_meth_card")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="🔙  رجوع", callback_data="back_to_main"))
    return b.as_markup()

def get_deposit_confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅  تأكيد الإيداع", callback_data="dep_confirm")
    b.button(text="❌  إلغاء",          callback_data="dep_cancel")
    b.adjust(2)
    return b.as_markup()

def get_retry_kb(action_cb: str, back_cb: str = "back_to_main") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔄  إعادة المحاولة", callback_data=action_cb)
    b.button(text="🔙  رجوع", callback_data=back_cb)
    b.adjust(2)
    return b.as_markup()


