import os
import random
import string
import uuid
import requests
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
from threading import Thread
import time

# ========== BOT CONFIGURATION ==========
BOT_TOKEN = "8991205577:AAHShpWxAFPoYwG5FRrDSwCnSseaXf2igtU"
ADMIN_ID = "6953529858"
STATS_FILE = "bot_stats.json"
ADMINS_FILE = "admins.json"
SETTINGS_FILE = "settings.json"
REFERRALS_FILE = "referrals.json"
REFERRAL_CONFIG_FILE = "referral_config.json"
COUPONS_FILE = "coupons.json"
# =======================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
user_sessions = {}

# ========== ADMIN PANEL FUNCTIONS ==========
def load_admins():
    try:
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, 'r') as f:
                return json.load(f)
        else:
            return {"admins": [ADMIN_ID], "admin_usernames": []}
    except:
        return {"admins": [ADMIN_ID], "admin_usernames": []}

def save_admins(admins_data):
    with open(ADMINS_FILE, 'w') as f:
        json.dump(admins_data, f, indent=4)

def is_admin(user_id):
    admins_data = load_admins()
    return str(user_id) in admins_data["admins"]

def promote_admin(user_id, username=None):
    admins_data = load_admins()
    if str(user_id) not in admins_data["admins"]:
        admins_data["admins"].append(str(user_id))
        if username:
            admins_data["admin_usernames"].append(username)
        save_admins(admins_data)
        return True
    return False

def demote_admin(user_id):
    if str(user_id) == ADMIN_ID:
        return False
    admins_data = load_admins()
    if str(user_id) in admins_data["admins"]:
        admins_data["admins"].remove(str(user_id))
        save_admins(admins_data)
        return True
    return False

# ========== SETTINGS FUNCTIONS ==========
def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            defaults = {
                "bot_active": True,
                "referral_system": False,
                "required_channels": [],
                "force_join": False,
                "require_points_for_reset": False,
                "points_per_reset": 5
            }
            for key, value in defaults.items():
                if key not in settings:
                    settings[key] = value
            return settings
        else:
            return {
                "bot_active": True,
                "referral_system": False,
                "required_channels": [],
                "force_join": False,
                "require_points_for_reset": False,
                "points_per_reset": 5
            }
    except:
        return {
            "bot_active": True,
            "referral_system": False,
            "required_channels": [],
            "force_join": False,
            "require_points_for_reset": False,
            "points_per_reset": 5
        }

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def add_channel(channel_username):
    settings = load_settings()
    if channel_username not in settings["required_channels"]:
        settings["required_channels"].append(channel_username)
        save_settings(settings)
        try:
            bot.send_message(ADMIN_ID, f"⚠️ <b>Channel Added:</b> @{channel_username}\n\nPlease add @{bot.get_me().username} as <b>administrator</b> in this channel for force join to work properly.\n\nMinimum permission: <code>Post Messages</code>", parse_mode='HTML')
        except:
            pass
        return True
    return False

def remove_channel(channel_username):
    settings = load_settings()
    if channel_username in settings["required_channels"]:
        settings["required_channels"].remove(channel_username)
        save_settings(settings)
        return True
    return False

# ========== REFERRAL SYSTEM (FIXED) ==========
def load_referral_config():
    try:
        if os.path.exists(REFERRAL_CONFIG_FILE):
            with open(REFERRAL_CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            return {
                "enabled": False,
                "points_per_referral": 10,
                "points_for_new_user": 5,   # NEW: points given to new user
                "min_referral_to_redeem": 1,
                "default_referral_points": 0
            }
    except:
        return {
            "enabled": False,
            "points_per_referral": 10,
            "points_for_new_user": 5,
            "min_referral_to_redeem": 1,
            "default_referral_points": 0
        }

def save_referral_config(config):
    with open(REFERRAL_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def load_coupons():
    try:
        if os.path.exists(COUPONS_FILE):
            with open(COUPONS_FILE, 'r') as f:
                return json.load(f)
        else:
            return {"coupons": {}}
    except:
        return {"coupons": {}}

def save_coupons(coupons_data):
    with open(COUPONS_FILE, 'w') as f:
        json.dump(coupons_data, f, indent=4)

def load_referrals():
    try:
        if os.path.exists(REFERRALS_FILE):
            with open(REFERRALS_FILE, 'r') as f:
                return json.load(f)
        else:
            return {"users": {}, "referral_counts": {}, "points": {}}
    except:
        return {"users": {}, "referral_counts": {}, "points": {}}

def save_referrals(referrals):
    with open(REFERRALS_FILE, 'w') as f:
        json.dump(referrals, f, indent=4)

def generate_referral_code(user_id):
    return f"REF{user_id}{random.randint(1000,9999)}"

def save_user_referral(user_id, referrer_id):
    config = load_referral_config()
    if not config["enabled"]:
        return False
    referrals = load_referrals()
    if str(user_id) not in referrals["users"]:
        # Record referral
        referrals["users"][str(user_id)] = {
            "referred_by": str(referrer_id),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        # Increase referrer's count and points
        referrals["referral_counts"][str(referrer_id)] = referrals["referral_counts"].get(str(referrer_id), 0) + 1
        points_for_referrer = config["points_per_referral"]
        referrals["points"][str(referrer_id)] = referrals["points"].get(str(referrer_id), 0) + points_for_referrer
        
        # Give points to the new user as well
        points_for_new = config.get("points_for_new_user", 5)
        referrals["points"][str(user_id)] = referrals["points"].get(str(user_id), 0) + points_for_new
        
        save_referrals(referrals)
        return True
    return False

def get_referral_count(user_id):
    referrals = load_referrals()
    return referrals["referral_counts"].get(str(user_id), 0)

def get_user_points(user_id):
    referrals = load_referrals()
    return referrals["points"].get(str(user_id), 0)

def add_points_to_user(user_id, points, reason="admin"):
    referrals = load_referrals()
    referrals["points"][str(user_id)] = referrals["points"].get(str(user_id), 0) + points
    save_referrals(referrals)
    return True

def deduct_points_for_reset(user_id):
    settings = load_settings()
    if not settings.get("require_points_for_reset", False):
        return True, 0
    points_needed = settings.get("points_per_reset", 5)
    current_points = get_user_points(user_id)
    if current_points < points_needed:
        return False, points_needed
    referrals = load_referrals()
    referrals["points"][str(user_id)] = current_points - points_needed
    save_referrals(referrals)
    return True, points_needed

def redeem_coupon(user_id, code):
    coupons = load_coupons()
    code = code.upper()
    if code not in coupons["coupons"]:
        return False, "Invalid coupon code"
    coupon = coupons["coupons"][code]
    if coupon["expiry"] and datetime.now().timestamp() > coupon["expiry"]:
        return False, "Coupon expired"
    if coupon["used_count"] >= coupon["max_uses"]:
        return False, "Coupon usage limit reached"
    if "min_referrals" in coupon and get_referral_count(user_id) < coupon["min_referrals"]:
        return False, f"You need at least {coupon['min_referrals']} referrals"
    if "max_referrals" in coupon and get_referral_count(user_id) > coupon["max_referrals"]:
        return False, f"Your referral count exceeds limit"
    add_points_to_user(user_id, coupon["points"], f"coupon {code}")
    coupons["coupons"][code]["used_count"] += 1
    coupons["coupons"][code]["used_by"].append(str(user_id))
    save_coupons(coupons)
    return True, f"✅ Redeemed {coupon['points']} points!"

def get_top_referrers(limit=10):
    referrals = load_referrals()
    sorted_users = sorted(referrals["points"].items(), key=lambda x: x[1], reverse=True)[:limit]
    return sorted_users

# ========== CHECK CHANNEL JOIN (FIXED) ==========
def check_channels_joined(user_id):
    settings = load_settings()
    if not settings["force_join"] or not settings["required_channels"]:
        return True
    for channel in settings["required_channels"]:
        try:
            chat_member = bot.get_chat_member(f"@{channel}", user_id)
            if chat_member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            print(f"Error checking {channel}: {e}")
            return False
    return True

def get_channels_buttons(user_id):
    settings = load_settings()
    keyboard = InlineKeyboardMarkup(row_width=1)
    unjoined_count = 0
    for channel in settings["required_channels"]:
        try:
            chat_member = bot.get_chat_member(f"@{channel}", user_id)
            if chat_member.status in ['member', 'administrator', 'creator']:
                continue
            else:
                keyboard.add(InlineKeyboardButton(f"📢 Join {channel}", url=f"https://t.me/{channel}"))
                unjoined_count += 1
        except Exception as e:
            keyboard.add(InlineKeyboardButton(f"📢 Join {channel}", url=f"https://t.me/{channel}"))
            unjoined_count += 1
    if unjoined_count > 0:
        keyboard.add(InlineKeyboardButton("✅ Check Join Status", callback_data="check_join"))
    else:
        keyboard.add(InlineKeyboardButton("✅ Verify", callback_data="check_join"))
    return keyboard

# ========== REAL STATISTICS FUNCTIONS ==========
def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        else:
            return {
                "total_resets": 0,
                "successful_resets": 0,
                "failed_resets": 0,
                "total_users": 0,
                "users": [],
                "last_reset": None
            }
    except:
        return {
            "total_resets": 0,
            "successful_resets": 0,
            "failed_resets": 0,
            "total_users": 0,
            "users": [],
            "last_reset": None
        }

def save_stats(stats):
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=4)
    except:
        pass

def update_stats(user_id, success=True):
    stats = load_stats()
    if user_id not in stats["users"]:
        stats["users"].append(user_id)
        stats["total_users"] = len(stats["users"])
    stats["total_resets"] += 1
    if success:
        stats["successful_resets"] += 1
    else:
        stats["failed_resets"] += 1
    stats["last_reset"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_stats(stats)
    return stats

def get_success_rate():
    stats = load_stats()
    if stats["total_resets"] > 0:
        return round((stats["successful_resets"] / stats["total_resets"]) * 100, 1)
    return 0

# ========== PERSISTENT KEYBOARD (WITH REDEEM BUTTON) ==========
def get_persistent_keyboard(is_user_admin=False):
    keyboard = ReplyKeyboardMarkup(
        row_width=2,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Press any button to continue..."
    )
    keyboard.add(
        KeyboardButton("🔄 RESET PASSWORD"),
        KeyboardButton("📖 HOW TO USE")
    )
    keyboard.add(
        KeyboardButton("📊 REAL STATISTICS"),
        KeyboardButton("👨‍💻 SUPPORT")
    )
    keyboard.add(
        KeyboardButton("📢 CHANNEL"),
        KeyboardButton("👤 MY PROFILE")
    )
    keyboard.add(
        KeyboardButton("🎁 REFERRAL"),
        KeyboardButton("🎫 REDEEM")   # NEW: Redeem button
    )
    if is_user_admin:
        keyboard.add(KeyboardButton("⚙️ ADMIN PANEL"))
    return keyboard

# ========== ADMIN PANEL KEYBOARDS ==========
def get_admin_panel():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 Bot Statistics", callback_data="admin_stats"),
        InlineKeyboardButton("👥 User List", callback_data="admin_users")
    )
    keyboard.add(
        InlineKeyboardButton("👑 Manage Admins", callback_data="admin_manage"),
        InlineKeyboardButton("📢 Manage Channels", callback_data="admin_channels")
    )
    keyboard.add(
        InlineKeyboardButton("🔄 Referral System", callback_data="admin_referral"),
        InlineKeyboardButton("🔌 Bot Status", callback_data="admin_bot_status")
    )
    keyboard.add(
        InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton("🏆 Leaderboard", callback_data="admin_leaderboard")
    )
    keyboard.add(
        InlineKeyboardButton("➕ Add Points", callback_data="admin_add_points"),
        InlineKeyboardButton("🎫 Manage Coupons", callback_data="admin_coupons")
    )
    keyboard.add(
        InlineKeyboardButton("⚙️ Reset Points", callback_data="admin_reset_points_config"),
        InlineKeyboardButton("❌ Close Panel", callback_data="close_panel")
    )
    return keyboard

def get_reset_points_config_keyboard():
    settings = load_settings()
    status = "✅ ON" if settings.get("require_points_for_reset", False) else "❌ OFF"
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(f"🔘 Toggle Requirement ({status})", callback_data="admin_toggle_points_require"),
        InlineKeyboardButton(f"⚙️ Set Points per Reset", callback_data="admin_set_points_per_reset")
    )
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_admin"))
    return keyboard

def get_admin_manage_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Promote Admin", callback_data="admin_promote"),
        InlineKeyboardButton("➖ Demote Admin", callback_data="admin_demote")
    )
    keyboard.add(
        InlineKeyboardButton("📋 View Admins", callback_data="admin_list"),
        InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")
    )
    return keyboard

def get_channel_manage_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Add Channel", callback_data="admin_add_channel"),
        InlineKeyboardButton("➖ Remove Channel", callback_data="admin_remove_channel")
    )
    keyboard.add(
        InlineKeyboardButton("📋 View Channels", callback_data="admin_view_channels"),
        InlineKeyboardButton("🔘 Toggle Force Join", callback_data="admin_toggle_force")
    )
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_admin"))
    return keyboard

def get_referral_manage_keyboard():
    config = load_referral_config()
    status = "✅ ON" if config["enabled"] else "❌ OFF"
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(f"🔄 Toggle ({status})", callback_data="admin_toggle_referral"),
        InlineKeyboardButton("⚙️ Set Points", callback_data="admin_set_points")
    )
    keyboard.add(
        InlineKeyboardButton("🌟 Set New User Points", callback_data="admin_set_newuser_points"),
        InlineKeyboardButton("📊 Referral Stats", callback_data="admin_ref_stats")
    )
    keyboard.add(
        InlineKeyboardButton("➕ Add Points", callback_data="admin_add_points"),
        InlineKeyboardButton("🎫 Manage Coupons", callback_data="admin_coupons")
    )
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_admin"))
    return keyboard

def get_coupon_manage_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Create Coupon", callback_data="admin_create_coupon"),
        InlineKeyboardButton("📋 List Coupons", callback_data="admin_list_coupons")
    )
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="admin_referral"))
    return keyboard

def get_cancel_inline():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("❌ CANCEL", callback_data="cancel"))
    return keyboard

# ========== ORIGINAL RESET FUNCTIONS ==========
def generate_device_info():
    ANDROID_ID = f"android-{''.join(random.choices(string.hexdigits.lower(), k=16))}"
    USER_AGENT = f"Instagram 394.0.0.46.81 Android ({random.choice(['28/9','29/10','30/11','31/12'])}; {random.choice(['240dpi','320dpi','480dpi'])}; {random.choice(['720x1280','1080x1920','1440x2560'])}; {random.choice(['samsung','xiaomi','huawei','oneplus','google'])}; {random.choice(['SM-G975F','Mi-9T','P30-Pro','ONEPLUS-A6003','Pixel-4'])}; intel; en_US; {random.randint(100000000,999999999)})"
    WATERFALL_ID = str(uuid.uuid4())
    timestamp = int(datetime.now().timestamp())
    nums = ''.join([str(random.randint(1, 100)) for _ in range(4)])
    PASSWORD = f'#PWD_INSTAGRAM:0:{timestamp}:Random@{nums}'
    return ANDROID_ID, USER_AGENT, WATERFALL_ID, PASSWORD

def make_headers(mid="", user_agent=""):
    return {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Bloks-Version-Id": "e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd",
        "X-Mid": mid,
        "User-Agent": user_agent,
    }

def id_user(user_id):
    try:
        url = f"https://i.instagram.com/api/v1/users/{user_id}/info/"
        headers = {"User-Agent": "Instagram 219.0.0.12.117 Android"}
        r = requests.get(url, headers=headers, timeout=10)
        username = r.json()["user"]["username"]
        return username
    except:
        return "Unknown"

def reset_instagram_password(reset_link):
    try:
        ANDROID_ID, USER_AGENT, WATERFALL_ID, PASSWORD = generate_device_info()
        uidb36 = reset_link.split("uidb36=")[1].split("&token=")[0]
        token = reset_link.split("&token=")[1].split(":")[0]
        url = "https://i.instagram.com/api/v1/accounts/password_reset/"
        data = {
            "source": "one_click_login_email",
            "uidb36": uidb36,
            "device_id": ANDROID_ID,
            "token": token,
            "waterfall_id": WATERFALL_ID
        }
        r = requests.post(url, headers=make_headers(user_agent=USER_AGENT), data=data, timeout=15)
        if "user_id" not in r.text:
            return {"success": False, "error": "Invalid or expired reset link"}
        mid = r.headers.get("Ig-Set-X-Mid")
        resp_json = r.json()
        user_id = resp_json.get("user_id")
        cni = resp_json.get("cni")
        nonce_code = resp_json.get("nonce_code")
        challenge_context = resp_json.get("challenge_context")
        url2 = "https://i.instagram.com/api/v1/bloks/apps/com.instagram.challenge.navigation.take_challenge/"
        data2 = {
            "user_id": str(user_id),
            "cni": str(cni),
            "nonce_code": str(nonce_code),
            "bk_client_context": '{"bloks_version":"e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd","styles_id":"instagram"}',
            "challenge_context": str(challenge_context),
            "bloks_versioning_id": "e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd",
            "get_challenge": "true"
        }
        r2 = requests.post(url2, headers=make_headers(mid, USER_AGENT), data=data2, timeout=15).text
        challenge_context_final = r2.replace('\\', '').split(f'(bk.action.i64.Const, {cni}), "')[1].split('", (bk.action.bool.Const, false)))')[0]
        data3 = {
            "is_caa": "False",
            "source": "",
            "uidb36": "",
            "error_state": {"type_name": "str", "index": 0, "state_id": 1048583541},
            "afv": "",
            "cni": str(cni),
            "token": "",
            "has_follow_up_screens": "0",
            "bk_client_context": {"bloks_version": "e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd", "styles_id": "instagram"},
            "challenge_context": challenge_context_final,
            "bloks_versioning_id": "e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd",
            "enc_new_password1": PASSWORD,
            "enc_new_password2": PASSWORD
        }
        requests.post(url2, headers=make_headers(mid, USER_AGENT), data=data3, timeout=15)
        new_password = PASSWORD.split(":")[-1]
        return {"success": True, "password": new_password, "user_id": user_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========== BOT COMMANDS ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = str(message.chat.id)
    settings = load_settings()
    if not settings["bot_active"] and not is_admin(user_id):
        bot.send_message(message.chat.id, "🔴 Bot is currently under maintenance. Please try again later.")
        return
    if settings["force_join"] and settings["required_channels"]:
        if not check_channels_joined(user_id):
            unjoined = []
            for ch in settings["required_channels"]:
                try:
                    chat_member = bot.get_chat_member(f"@{ch}", user_id)
                    if chat_member.status in ['left', 'kicked']:
                        unjoined.append(f"📢 @{ch}")
                except:
                    unjoined.append(f"📢 @{ch}")
            channels_text = "\n".join(unjoined) if unjoined else "Please click verify below"
            join_msg = f"""
╔═════════════════════════════╗
║     🔐 <b>CHANNELS REQUIRED</b> 🔐      
╠═════════════════════════════╣
║  {channels_text}                      
║  After joining, click the button below.
╚═════════════════════════════╝
"""
            bot.send_message(message.chat.id, join_msg, reply_markup=get_channels_buttons(user_id))
            return
    config = load_referral_config()
    # FIXED: correctly extract referrer ID
    if config["enabled"] and len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        if ref_code.startswith("REF"):
            # Remove "REF" prefix and last 4 random digits
            referrer_id = ref_code[3:-4]   # FIXED
            save_user_referral(user_id, referrer_id)
    welcome_text = f"""
╔═════════════════════════════╗
║      <i>INSTAGRAM PASS RESET BOT</i>     
╠═════════════════════════════╣
║  🔐 <b>Welcome {message.from_user.first_name}!</b> 
║  ⚡ Features :- 
║  • Instant Password Reset
║  • Secure reset
╠═════════════════════════════╣
║  👤 Dev :- @J15H4NN               
║  📢 Channel :- @j15h4n            
╚═════════════════════════════╝
"""
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_persistent_keyboard(is_admin(user_id)))

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if is_admin(str(message.chat.id)):
        admin_panel(message)
    else:
        bot.send_message(message.chat.id, "❌ Unauthorized.")

@bot.message_handler(commands=['profile'])
def profile_command(message):
    user_id = str(message.chat.id)
    points = get_user_points(user_id)
    referrals_count = get_referral_count(user_id)
    ref_code = generate_referral_code(user_id)
    config = load_referral_config()
    profile_text = f"""
╔═════════════════════════════╗
║         👤 <b>MY PROFILE</b> 👤          
╠═════════════════════════════╣
║  🆔 User ID :- <code>{user_id}</code>      
║  ⭐ Points :- <b>{points}</b>              
║  👥 Referrals :- <b>{referrals_count}</b>  
║  🔗 Referral Link :-          
║  <code>https://t.me/{bot.get_me().username}?start={ref_code}</code>
║  💡 Points per referral :- {config['points_per_referral']}
╚═════════════════════════════╝
"""
    bot.send_message(message.chat.id, profile_text, parse_mode='HTML')

@bot.message_handler(commands=['referral'])
def referral_command(message):
    user_id = str(message.chat.id)
    config = load_referral_config()
    if not config["enabled"]:
        bot.reply_to(message, "❌ Referral system disabled.")
        return
    ref_code = generate_referral_code(user_id)
    points = get_user_points(user_id)
    count = get_referral_count(user_id)
    bot.reply_to(message, f"🎁 <b>Your Referral Info</b>\n\n🔗 <code>https://t.me/{bot.get_me().username}?start={ref_code}</code>\n\n👥 Referrals: {count}\n⭐ Points: {points}\n\nEach referral gives {config['points_per_referral']} points!", parse_mode='HTML')

@bot.message_handler(commands=['points'])
def points_command(message):
    user_id = str(message.chat.id)
    points = get_user_points(user_id)
    bot.reply_to(message, f"⭐ <b>Your Points:</b> {points}", parse_mode='HTML')

@bot.message_handler(commands=['redeem'])
def redeem_command(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage: /redeem COUPON_CODE")
        return
    code = args[1].upper()
    success, msg = redeem_coupon(str(message.chat.id), code)
    bot.reply_to(message, msg)

@bot.message_handler(commands=['leaderboard'])
def leaderboard_command(message):
    top = get_top_referrers(10)
    if not top:
        bot.reply_to(message, "No data yet.")
        return
    text = "🏆 <b>Top Referrers by Points</b>\n\n"
    for i, (uid, pts) in enumerate(top, 1):
        try:
            name = bot.get_chat(uid).first_name
        except:
            name = uid
        text += f"{i}. {name} — {pts} pts\n"
    bot.reply_to(message, text, parse_mode='HTML')

# ========== ADMIN PANEL HANDLER ==========
@bot.message_handler(func=lambda message: message.text == "⚙️ ADMIN PANEL")
def admin_panel(message):
    if not is_admin(str(message.chat.id)):
        bot.send_message(message.chat.id, "❌ Unauthorized.")
        return
    admin_text = "⚙️ ADMIN CONTROL PANEL\nSelect an option:"
    bot.send_message(message.chat.id, admin_text, reply_markup=get_admin_panel())

# ========== CALLBACK HANDLER ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.message.chat.id)
    
    if not is_admin(user_id) and call.data not in ["check_join", "cancel"]:
        bot.answer_callback_query(call.id, "❌ Unauthorized!", show_alert=True)
        return

    if call.data == "check_join":
        if check_channels_joined(user_id):
            bot.edit_message_text("✅ You have joined all channels! Use /start to continue.", call.message.chat.id, call.message.message_id)
            start_command(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ You haven't joined all channels yet! Please join all required channels and try again.", show_alert=True)
        return

    if call.data == "cancel":
        bot.edit_message_text("❌ Cancelled.", call.message.chat.id, call.message.message_id, reply_markup=get_persistent_keyboard(is_admin(user_id)))
        if user_id in user_sessions:
            del user_sessions[user_id]
        return

    if not is_admin(user_id):
        return

    # Admin callbacks
    if call.data == "admin_stats":
        stats = load_stats()
        success_rate = get_success_rate()
        admins_data = load_admins()
        settings = load_settings()
        text = f"""
📊 STATISTICS
✅ Success: {stats['successful_resets']}
❌ Failed: {stats['failed_resets']}
🔄 Total: {stats['total_resets']}
📊 Rate: {success_rate}%
👤 Users: {stats['total_users']}
👑 Admins: {len(admins_data['admins'])}
🔌 Bot: {'Active' if settings['bot_active'] else 'Inactive'}
🔄 Referral: {'ON' if settings['referral_system'] else 'OFF'}
🔒 Force Join: {'ON' if settings['force_join'] else 'OFF'}
💰 Points per Reset: {settings.get('points_per_reset',5)} (Require: {'ON' if settings.get('require_points_for_reset',False) else 'OFF'})
⏰ Last Reset: {stats['last_reset'] or 'Never'}
"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_admin_panel())
        return

    elif call.data == "admin_users":
        stats = load_stats()
        users_list = "\n".join([f"👤 `{uid}`" for uid in stats['users'][:20]]) or "None"
        text = f"Total Users: {stats['total_users']}\n\nRecent:\n{users_list}"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_admin_panel())
        return

    elif call.data == "admin_manage":
        bot.edit_message_text("👑 Admin Management", call.message.chat.id, call.message.message_id, reply_markup=get_admin_manage_keyboard())
        return

    elif call.data == "admin_channels":
        bot.edit_message_text("📢 Channel Management", call.message.chat.id, call.message.message_id, reply_markup=get_channel_manage_keyboard())
        return

    elif call.data == "admin_referral":
        bot.edit_message_text("🔄 Referral System", call.message.chat.id, call.message.message_id, reply_markup=get_referral_manage_keyboard())
        return

    elif call.data == "admin_bot_status":
        settings = load_settings()
        status = "🟢 ACTIVE" if settings["bot_active"] else "🔴 INACTIVE"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(f"Set {'Inactive' if settings['bot_active'] else 'Active'}", callback_data="admin_toggle_bot"))
        kb.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_admin"))
        bot.edit_message_text(f"Bot Status: {status}", call.message.chat.id, call.message.message_id, reply_markup=kb)
        return

    elif call.data == "admin_broadcast":
        bot.edit_message_text("📢 Send broadcast message:", call.message.chat.id, call.message.message_id)
        user_sessions[user_id] = {"state": "waiting_for_broadcast"}
        return

    elif call.data == "admin_reset_points_config":
        bot.edit_message_text("⚙️ Points Requirement for Reset", call.message.chat.id, call.message.message_id, reply_markup=get_reset_points_config_keyboard())
        return

    elif call.data == "admin_toggle_points_require":
        settings = load_settings()
        settings["require_points_for_reset"] = not settings.get("require_points_for_reset", False)
        save_settings(settings)
        status = "ON" if settings["require_points_for_reset"] else "OFF"
        bot.answer_callback_query(call.id, f"Points requirement turned {status}")
        bot.edit_message_text(f"✅ Points requirement is now {status}", call.message.chat.id, call.message.message_id, reply_markup=get_reset_points_config_keyboard())
        return

    elif call.data == "admin_set_points_per_reset":
        bot.edit_message_text("Send points required per reset (number):", call.message.chat.id, call.message.message_id)
        user_sessions[user_id] = {"state": "waiting_set_points_per_reset"}
        return

    elif call.data == "admin_toggle_bot":
        settings = load_settings()
        settings["bot_active"] = not settings["bot_active"]
        save_settings(settings)
        status = "ACTIVE" if settings["bot_active"] else "INACTIVE"
        bot.answer_callback_query(call.id, f"Bot is now {status}")
        bot.edit_message_text("✅ Bot status updated", call.message.chat.id, call.message.message_id, reply_markup=get_admin_panel())
        return

    elif call.data == "admin_toggle_referral":
        config = load_referral_config()
        config["enabled"] = not config["enabled"]
        save_referral_config(config)
        settings = load_settings()
        settings["referral_system"] = config["enabled"]
        save_settings(settings)
        status = "ON" if config["enabled"] else "OFF"
        bot.answer_callback_query(call.id, f"Referral System {status}")
        bot.edit_message_text("✅ Referral system updated", call.message.chat.id, call.message.message_id, reply_markup=get_referral_manage_keyboard())
        return

    elif call.data == "admin_set_points":
        bot.edit_message_text("Send points per referral (number):", call.message.chat.id, call.message.message_id)
        user_sessions[user_id] = {"state": "waiting_set_points"}
        return

    elif call.data == "admin_set_newuser_points":
        bot.edit_message_text("Send points to give to new user when they join via referral link (number):", call.message.chat.id, call.message.message_id)
        user_sessions[user_id] = {"state": "waiting_set_newuser_points"}
        return

    elif call.data == "admin_ref_stats":
        referrals = load_referrals()
        top = get_top_referrers(5)
        text = f"📊 Referral Stats\nTotal referred: {len(referrals['users'])}\nTotal points: {sum(referrals['points'].values())}\n"
        if top:
            text += "\n🏆 Top 5:\n"
            for uid, pts in top:
                try:
                    name = bot.get_chat(uid).first_name
                except:
                    name = uid
                text += f"{name}: {pts} pts\n"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_referral_manage_keyboard())
        return

    elif call.data == "admin_add_points":
        bot.edit_message_text("Send `user_id points` or `@username points`", call.message.chat.id, call.message.message_id)
        user_sessions[user_id] = {"state": "waiting_add_points"}
        return

    elif call.data == "admin_coupons":
        bot.edit_message_text("🎫 Coupon Management", call.message.chat.id, call.message.message_id, reply_markup=get_coupon_manage_keyboard())
        return

    elif call.data == "admin_create_coupon":
        bot.edit_message_text("Create coupon: `CODE points max_uses min_ref max_ref expiry_days`\nExample: `WELCOME10 10 100 5 100 30`", call.message.chat.id, call.message.message_id)
        user_sessions[user_id] = {"state": "waiting_create_coupon"}
        return

    elif call.data == "admin_list_coupons":
        coupons = load_coupons()
        if not coupons["coupons"]:
            text = "No coupons."
        else:
            text = "🎫 Active Coupons:\n"
            for code, info in coupons["coupons"].items():
                exp = "Never" if info["expiry"] == 0 else datetime.fromtimestamp(info["expiry"]).strftime("%Y-%m-%d")
                text += f"`{code}`: {info['points']} pts | used {info['used_count']}/{info['max_uses']} | min ref {info.get('min_referrals',0)} | exp {exp}\n"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=get_coupon_manage_keyboard())
        return

    elif call.data == "admin_leaderboard":
        top = get_top_referrers(10)
        if not top:
            text = "No data."
        else:
            text = "🏆 Top 10 by Points\n"
            for i, (uid, pts) in enumerate(top, 1):
                try:
                    name = bot.get_chat(uid).first_name
                except:
                    name = uid
                text += f"{i}. {name} — {pts}\n"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=get_admin_panel())
        return

    elif call.data == "back_to_admin":
        admin_panel(call.message)
        return

    elif call.data == "close_panel":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start_command(call.message)
        return

    # Admin management sub-menu callbacks
    elif call.data == "admin_promote":
        bot.edit_message_text("Send user ID or @username to promote:", call.message.chat.id, call.message.message_id)
        user_sessions[user_id] = {"state": "waiting_for_promote"}
        return

    elif call.data == "admin_demote":
        bot.edit_message_text("Send user ID to demote:", call.message.chat.id, call.message.message_id)
        user_sessions[user_id] = {"state": "waiting_for_demote"}
        return

    elif call.data == "admin_list":
        admins_data = load_admins()
        text = "Admins:\n" + "\n".join([f"👑 `{a}`" for a in admins_data["admins"]])
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_admin_manage_keyboard())
        return

    elif call.data == "admin_add_channel":
        bot.edit_message_text("Send channel username (without @):", call.message.chat.id, call.message.message_id)
        user_sessions[user_id] = {"state": "waiting_for_add_channel"}
        return

    elif call.data == "admin_remove_channel":
        settings = load_settings()
        if not settings["required_channels"]:
            bot.edit_message_text("No channels to remove.", call.message.chat.id, call.message.message_id, reply_markup=get_channel_manage_keyboard())
        else:
            kb = InlineKeyboardMarkup(row_width=1)
            for ch in settings["required_channels"]:
                kb.add(InlineKeyboardButton(f"❌ @{ch}", callback_data=f"remove_ch_{ch}"))
            kb.add(InlineKeyboardButton("🔙 Back", callback_data="admin_channels"))
            bot.edit_message_text("Select channel to remove:", call.message.chat.id, call.message.message_id, reply_markup=kb)
        return

    elif call.data.startswith("remove_ch_"):
        ch = call.data.replace("remove_ch_", "")
        remove_channel(ch)
        bot.answer_callback_query(call.id, f"Removed @{ch}")
        bot.edit_message_text("Channel removed.", call.message.chat.id, call.message.message_id, reply_markup=get_channel_manage_keyboard())
        return

    elif call.data == "admin_view_channels":
        settings = load_settings()
        ch_list = "\n".join([f"📢 @{c}" for c in settings["required_channels"]]) or "None"
        text = f"Force Join: {'ON' if settings['force_join'] else 'OFF'}\nChannels:\n{ch_list}"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_channel_manage_keyboard())
        return

    elif call.data == "admin_toggle_force":
        settings = load_settings()
        settings["force_join"] = not settings["force_join"]
        save_settings(settings)
        bot.answer_callback_query(call.id, f"Force Join {'ON' if settings['force_join'] else 'OFF'}")
        bot.edit_message_text("Updated.", call.message.chat.id, call.message.message_id, reply_markup=get_channel_manage_keyboard())
        return

# ========== MESSAGE HANDLERS ==========
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = str(message.chat.id)

    # Handle admin state inputs
    if user_id in user_sessions:
        session = user_sessions[user_id]
        state = session.get("state")

        if state == "waiting_for_broadcast":
            stats = load_stats()
            success, fail = 0, 0
            for uid in stats["users"]:
                try:
                    bot.send_message(uid, f"📢 Broadcast\n\n{message.text}")
                    success += 1
                    time.sleep(0.05)
                except:
                    fail += 1
            bot.send_message(user_id, f"✅ Sent: {success}, Failed: {fail}")
            del user_sessions[user_id]
            start_command(message)
            return

        elif state == "waiting_for_promote":
            target = message.text.strip()
            target_id = target
            if target.startswith("@"):
                try:
                    target_id = bot.get_chat(target).id
                except:
                    bot.send_message(user_id, "Invalid username")
                    return
            if promote_admin(target_id, target if target.startswith("@") else None):
                bot.send_message(user_id, f"✅ Promoted {target}")
            else:
                bot.send_message(user_id, "❌ Failed (already admin?)")
            del user_sessions[user_id]
            start_command(message)
            return

        elif state == "waiting_for_demote":
            target_id = message.text.strip()
            if demote_admin(target_id):
                bot.send_message(user_id, f"✅ Demoted {target_id}")
            else:
                bot.send_message(user_id, "❌ Failed (main admin)")
            del user_sessions[user_id]
            start_command(message)
            return

        elif state == "waiting_for_add_channel":
            channel = message.text.strip().replace("@", "")
            if add_channel(channel):
                bot.send_message(user_id, f"✅ Added @{channel}")
            else:
                bot.send_message(user_id, "❌ Already exists")
            del user_sessions[user_id]
            start_command(message)
            return

        elif state == "waiting_set_points":
            try:
                points = int(message.text.strip())
                config = load_referral_config()
                config["points_per_referral"] = points
                save_referral_config(config)
                bot.send_message(user_id, f"✅ Points per referral set to {points}")
            except:
                bot.send_message(user_id, "❌ Invalid number")
            del user_sessions[user_id]
            start_command(message)
            return

        elif state == "waiting_set_points_per_reset":
            try:
                points = int(message.text.strip())
                settings = load_settings()
                settings["points_per_reset"] = points
                save_settings(settings)
                bot.send_message(user_id, f"✅ Points per reset set to {points}")
            except:
                bot.send_message(user_id, "❌ Invalid number")
            del user_sessions[user_id]
            start_command(message)
            return

        elif state == "waiting_set_newuser_points":
            try:
                points = int(message.text.strip())
                config = load_referral_config()
                config["points_for_new_user"] = points
                save_referral_config(config)
                bot.send_message(user_id, f"✅ Points for new user set to {points}")
            except:
                bot.send_message(user_id, "❌ Invalid number")
            del user_sessions[user_id]
            start_command(message)
            return

        elif state == "waiting_add_points":
            parts = message.text.strip().split()
            if len(parts) < 2:
                bot.send_message(user_id, "❌ Format: user_id points")
                return
            target = parts[0]
            try:
                pts = int(parts[1])
            except:
                bot.send_message(user_id, "❌ Points must be number")
                return
            if target.startswith("@"):
                try:
                    target_id = bot.get_chat(target).id
                except:
                    bot.send_message(user_id, "❌ Invalid username")
                    return
            else:
                target_id = target
            if add_points_to_user(target_id, pts, "admin"):
                bot.send_message(user_id, f"✅ Added {pts} points to {target}")
            else:
                bot.send_message(user_id, "❌ Failed")
            del user_sessions[user_id]
            start_command(message)
            return

        elif state == "waiting_create_coupon":
            parts = message.text.strip().split()
            if len(parts) < 4:
                bot.send_message(user_id, "❌ Format: CODE points max_uses min_ref max_ref expiry_days")
                return
            code = parts[0].upper()
            try:
                pts = int(parts[1])
                max_uses = int(parts[2])
                min_ref = int(parts[3])
                max_ref = int(parts[4]) if len(parts) > 4 else 999999
                expiry_days = int(parts[5]) if len(parts) > 5 else 0
            except:
                bot.send_message(user_id, "❌ All values must be numbers")
                return
            expiry = 0
            if expiry_days > 0:
                expiry = int(time.time()) + expiry_days * 86400
            coupons = load_coupons()
            if code in coupons["coupons"]:
                bot.send_message(user_id, "❌ Coupon exists")
                return
            coupons["coupons"][code] = {
                "points": pts,
                "max_uses": max_uses,
                "used_count": 0,
                "used_by": [],
                "min_referrals": min_ref,
                "max_referrals": max_ref,
                "expiry": expiry,
                "created_at": int(time.time())
            }
            save_coupons(coupons)
            bot.send_message(user_id, f"✅ Coupon {code} created")
            del user_sessions[user_id]
            start_command(message)
            return

        elif state == "waiting_for_link":   # For password reset
            settings = load_settings()
            if settings.get("require_points_for_reset", False):
                needed = settings.get("points_per_reset", 5)
                user_points = get_user_points(user_id)
                if user_points < needed:
                    bot.send_message(message.chat.id, f"❌ You need {needed} points to reset password.\nYour points: {user_points}")
                    del user_sessions[user_id]
                    return
            reset_link = message.text.strip()
            if "instagram.com" in reset_link and "password/reset" in reset_link:
                processing = bot.send_message(message.chat.id, "⏳ Processing...")
                result = reset_instagram_password(reset_link)
                if result.get("success"):
                    user_id_ig = result.get("user_id")
                    new_password = result.get("password")
                    username = id_user(user_id_ig)
                    can_proceed, needed_pts = deduct_points_for_reset(user_id)
                    if not can_proceed:
                        bot.edit_message_text(f"❌ Insufficient points! Need {needed_pts}.", message.chat.id, processing.message_id)
                        del user_sessions[user_id]
                        return
                    update_stats(user_id, True)
                    success_msg = f"✅ RESET SUCCESSFUL\n👤 {username}\n🔑 `{new_password}`"
                    bot.edit_message_text(success_msg, message.chat.id, processing.message_id, parse_mode='Markdown')
                    if settings.get("require_points_for_reset", False):
                        bot.send_message(message.chat.id, f"💸 {needed_pts} points deducted. Remaining: {get_user_points(user_id)}")
                else:
                    update_stats(user_id, False)
                    bot.edit_message_text("❌ Reset failed. Link may be expired/invalid.", message.chat.id, processing.message_id)
            else:
                bot.send_message(message.chat.id, "❌ Invalid Instagram reset link.")
            del user_sessions[user_id]
            return

        elif state == "waiting_for_redeem":   # New state for redeem button
            code = message.text.strip().upper()
            success, msg = redeem_coupon(user_id, code)
            bot.send_message(message.chat.id, msg)
            del user_sessions[user_id]
            return

    # BUTTON HANDLERS (including new REDEEM button)
    if message.text in ["🔄 RESET PASSWORD", "📖 HOW TO USE", "📊 REAL STATISTICS", "👨‍💻 SUPPORT", "📢 CHANNEL", "👤 MY PROFILE", "🎁 REFERRAL", "🎫 REDEEM", "⚙️ ADMIN PANEL"]:
        if message.text == "🔄 RESET PASSWORD":
            settings = load_settings()
            if settings.get("require_points_for_reset", False):
                needed = settings.get("points_per_reset", 5)
                user_points = get_user_points(user_id)
                if user_points < needed:
                    bot.send_message(message.chat.id, f"❌ You need {needed} points to reset password!\nYour current points: {user_points}\nEarn points via referrals or coupons.")
                    return
            reset_text = f"""
╔═════════════════════════════╗
║    🔄 <b>PASSWORD RESET MODE</b> 🔄     
╠═════════════════════════════╣
║  📎 <b>Send me your Instagram reset link</b>
║  ⏳ <i>Processing takes 5-10 sec</i>    
╠═════════════════════════════╣
║  ⚡ <i>Send the link NOW...</i>         
╚═════════════════════════════╝
"""
            bot.send_message(message.chat.id, reset_text, reply_markup=get_cancel_inline())
            user_sessions[user_id] = {"state": "waiting_for_link"}

        elif message.text == "📖 HOW TO USE":
            help_text = f"""
╔═════════════════════════════╗
║        ❓ <b>HOW TO USE</b> ❓          
╠═════════════════════════════╣
║  <b>📝 STEPS TO RESET PASSWORD :-</b>    
║                                      
║  <b>1️⃣</b> Go to Instagram Login       
║  <b>2️⃣</b> Click "Forgot Password"     
║  <b>3️⃣</b> Enter username/email        
║  <b>4️⃣</b> Check email/SMS for link    
║  <b>5️⃣</b> Copy the full reset link    
║  <b>6️⃣</b> Click RESET PASSWORD button 
║  <b>7️⃣</b> Send link to this bot       
║  <b>8️⃣</b> Wait 5-10 seconds          
║  <b>9️⃣</b> Get new password!           
╠═════════════════════════════╣
║  ⚠️ <b>NOTE :-</b> Link must be fresh!      
╚═════════════════════════════╝
"""
            bot.send_message(message.chat.id, help_text, reply_markup=get_persistent_keyboard(is_admin(user_id)))

        elif message.text == "📊 REAL STATISTICS":
            stats = load_stats()
            success_rate = get_success_rate()
            stats_text = f"""
╔═════════════════════════════╗
║       📊 <b>STATISTICS</b> 📊         
╠═════════════════════════════╣
║  🟢 <b>Bot Status:</b> <i>Online</i>       
║                                      
║  📈 <b>Reset Statistics:</b>            
║  ┌───────────────────────────┐  
║  │ ✅ Successful :- <b>{stats['successful_resets']}</b>      
║  │ ❌ Failed :- <b>{stats['failed_resets']}</b>          
║  │ 🔄 Total Resets :- <b>{stats['total_resets']}</b>     
║  │ 📊 Success Rate :- <b>{success_rate}%</b>            
║  └───────────────────────────┘  
║                                      
║  👥 <b>User Statistics :-</b>             
║  ┌───────────────────────────┐  
║  │ 👤 Total Users :- <b>{stats['total_users']}</b>   
║  └───────────────────────────┘  
║                                      
╠═════════════════════════════╣
║  ⏰ <b>Last Reset :-</b> <i>{stats['last_reset'] or 'No resets yet'}</i>     
╠═════════════════════════════╣
║  🚀 <i>Updated in real-time</i>         
╚═════════════════════════════╝
"""
            bot.send_message(message.chat.id, stats_text, reply_markup=get_persistent_keyboard(is_admin(user_id)))

        elif message.text == "👨‍💻 SUPPORT":
            support_text = f"""
╔═════════════════════════════╗
║       💬 <b>SUPPORT CENTER</b> 💬       
╠═════════════════════════════╣
║  <b>📞 Contact Developer :-</b>  <code>@J15H4NN</code>                                             
║  <b>📢 Official Channel :-</b>  <code>@j15h4n</code>               
║                                      
║  <b>❓ Common Issues :-</b>              
║  • Link expired? Get fresh link      
║  • Already used? Request new one     
║  • Invalid format? Check link        
╠═════════════════════════════╣
║  💡 <i>DM for 24/7 support</i>         
╚═════════════════════════════╝
"""
            bot.send_message(message.chat.id, support_text, reply_markup=get_persistent_keyboard(is_admin(user_id)))

        elif message.text == "📢 CHANNEL":
            channel_text = f"""
╔═════════════════════════════╗
║        📢 <b>OFFICIAL CHANNEL</b> 📢      
╠═════════════════════════════╣
║  📣 <b>Join our channel for :-</b>        
║  • Latest Updates                    
║  • New Features                      
║  • Free Tools                        
║  • 24/7 Support                      
║                                      
║  🔗 <b>Link :-</b> @j15h4n               
╠═════════════════════════════╣
╚═════════════════════════════╝
"""
            bot.send_message(message.chat.id, channel_text, reply_markup=get_persistent_keyboard(is_admin(user_id)))

        elif message.text == "👤 MY PROFILE":
            profile_command(message)
        elif message.text == "🎁 REFERRAL":
            referral_command(message)
        elif message.text == "🎫 REDEEM":
            bot.send_message(message.chat.id, "📎 Please send your coupon code:", reply_markup=get_cancel_inline())
            user_sessions[user_id] = {"state": "waiting_for_redeem"}
        elif message.text == "⚙️ ADMIN PANEL" and is_admin(user_id):
            admin_panel(message)
        return

    # If it's a normal message but not a button and not in a state
    settings = load_settings()
    if not settings["bot_active"] and not is_admin(user_id):
        bot.send_message(message.chat.id, "🔴 Bot under maintenance")
        return
    if settings["force_join"] and settings["required_channels"] and not check_channels_joined(user_id):
        bot.send_message(message.chat.id, "Please join required channels first.")
        return
    if "instagram.com" in message.text and "password/reset" in message.text:
        # Already handled in waiting_for_link state, but if user directly sends link without pressing button
        if settings.get("require_points_for_reset", False):
            needed = settings.get("points_per_reset", 5)
            user_points = get_user_points(user_id)
            if user_points < needed:
                bot.send_message(message.chat.id, f"❌ You need {needed} points to reset password.\nYour points: {user_points}")
                return
        reset_link = message.text.strip()
        processing = bot.send_message(message.chat.id, "⏳ Processing...")
        result = reset_instagram_password(reset_link)
        if result.get("success"):
            user_id_ig = result.get("user_id")
            new_password = result.get("password")
            username = id_user(user_id_ig)
            can_proceed, needed_pts = deduct_points_for_reset(user_id)
            if not can_proceed:
                bot.edit_message_text(f"❌ Insufficient points! Need {needed_pts}.", message.chat.id, processing.message_id)
                return
            update_stats(user_id, True)
            success_msg = f"✅ RESET SUCCESSFUL\n👤 {username}\n🔑 `{new_password}`"
            bot.edit_message_text(success_msg, message.chat.id, processing.message_id, parse_mode='Markdown')
            if settings.get("require_points_for_reset", False):
                bot.send_message(message.chat.id, f"💸 {needed_pts} points deducted. Remaining: {get_user_points(user_id)}")
        else:
            update_stats(user_id, False)
            bot.edit_message_text("❌ Reset failed. Link may be expired/invalid.", message.chat.id, processing.message_id)
    else:
        if is_admin(user_id):
            bot.send_message(message.chat.id, "❌ Invalid command. Use buttons below.", reply_markup=get_persistent_keyboard(True))
        else:
            bot.send_message(message.chat.id, "❌ Invalid command. Use buttons below.", reply_markup=get_persistent_keyboard(False))

if __name__ == "__main__":
    print("🟢 Bot started! Press Ctrl+C to stop.")
    bot.infinity_polling()