#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 GAME STUDIO TELEGRAM BOT
============================
Tam kapsamlı oyun stüdyosu grup botu
Özellikler:
  - Yeni üye karşılama (animasyonlu mesajlar)
  - Puan sistemi (XP + altın)
  - Seviye sistemi (30 seviye)
  - Liderlik tablosu
  - Günlük bonus
  - Başarı rozetleri
  - Trivia oyunu
  - Zararlı kelime filtresi
  - Moderasyon araçları
  - Mini oyunlar (zar, yazı-tura, kelime oyunu)
  - Özel unvanlar
  - Profil kartı
"""

import json
import os
import random
import logging
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, ChatMemberUpdated
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatMemberHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
#  GROQ AI İSTEMCİSİ
# ─────────────────────────────────────────────
try:
    from groq import Groq as GroqClient
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GameStudioBot")

# ─────────────────────────────────────────────
#  YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────

def load_config() -> dict:
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_data() -> dict:
    if not os.path.exists("data.json"):
        return {"users": {}, "group_stats": {"total_messages": 0, "total_commands": 0}}
    with open("data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data: dict):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(data: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "xp": 0,
            "gold": 0,
            "level": 1,
            "messages": 0,
            "commands_used": 0,
            "daily_streak": 0,
            "last_daily": None,
            "last_message_time": None,
            "username": None,
            "first_name": None,
            "join_date": datetime.now().isoformat(),
            "achievements": [],
            "title": None,
            "warnings": 0,
            "is_banned": False,
            "trivia_correct": 0,
            "trivia_total": 0,
            "inventory": [],
            "total_xp_earned": 0,
        }
    return data["users"][uid]

def xp_for_level(level: int) -> int:
    """Her seviye için gereken toplam XP"""
    return int(100 * (level ** 1.6))

def calculate_level(xp: int) -> int:
    level = 1
    while level < 30 and xp >= xp_for_level(level + 1):
        level += 1
    return level

def get_rank_info(level: int) -> dict:
    cfg = load_config()
    ranks = cfg["ranks"]
    for rank in reversed(ranks):
        if level >= rank["min_level"]:
            return rank
    return ranks[0]

def progress_bar(current: int, maximum: int, length: int = 10) -> str:
    filled = int((current / maximum) * length) if maximum > 0 else 0
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

def check_achievements(user: dict, data: dict) -> list:
    """Kullanıcının yeni kazandığı başarıları döndür"""
    cfg = load_config()
    new_achievements = []
    for ach in cfg["achievements"]:
        if ach["id"] in user["achievements"]:
            continue
        earned = False
        cond = ach["condition"]
        if cond["type"] == "messages" and user["messages"] >= cond["value"]:
            earned = True
        elif cond["type"] == "level" and user["level"] >= cond["value"]:
            earned = True
        elif cond["type"] == "streak" and user["daily_streak"] >= cond["value"]:
            earned = True
        elif cond["type"] == "trivia" and user["trivia_correct"] >= cond["value"]:
            earned = True
        elif cond["type"] == "gold" and user["gold"] >= cond["value"]:
            earned = True
        if earned:
            user["achievements"].append(ach["id"])
            user["xp"] += ach.get("reward_xp", 0)
            user["gold"] += ach.get("reward_gold", 0)
            new_achievements.append(ach)
    return new_achievements

def mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'

# ─────────────────────────────────────────────
#  KARŞILAMA - YENİ ÜYE
# ─────────────────────────────────────────────

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    data = load_data()

    result: ChatMemberUpdated = update.chat_member
    if result.new_chat_member.status not in ["member", "restricted"]:
        return
    if result.old_chat_member.status in ["member", "administrator", "creator"]:
        return

    user = result.new_chat_member.user
    if user.is_bot:
        return

    db_user = get_user(data, user.id)
    db_user["username"] = user.username
    db_user["first_name"] = user.first_name

    # Yeni üyeye başlangıç bonusu
    db_user["xp"] += cfg["rewards"]["join_bonus_xp"]
    db_user["gold"] += cfg["rewards"]["join_bonus_gold"]
    db_user["total_xp_earned"] += cfg["rewards"]["join_bonus_xp"]
    save_data(data)

    welcome_msg = random.choice(cfg["messages"]["welcome"])
    rank = get_rank_info(db_user["level"])

    msg = (
        f"╔══════════════════════╗\n"
        f"║  🎮 HOŞ GELDİN, {user.first_name[:12]}!  ║\n"
        f"╚══════════════════════╝\n\n"
        f"{welcome_msg}\n\n"
        f"🏅 Başlangıç Rankın: <b>{rank['emoji']} {rank['name']}</b>\n"
        f"⚡ Başlangıç XP: <b>+{cfg['rewards']['join_bonus_xp']}</b>\n"
        f"💰 Başlangıç Altın: <b>+{cfg['rewards']['join_bonus_gold']}</b>\n\n"
        f"📌 /yardim yazarak komutları görebilirsin!\n"
        f"🎯 Aktif ol, puan kazan, liderlik tablosuna çık!"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Profilim", callback_data=f"profile_{user.id}"),
         InlineKeyboardButton("🏆 Liderlik", callback_data="leaderboard_1")],
        [InlineKeyboardButton("🎮 Oyunlar", callback_data="games_menu"),
         InlineKeyboardButton("📖 Yardım", callback_data="help_menu")]
    ])

    await context.bot.send_message(
        chat_id=result.chat.id,
        text=msg,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

    # Başarı kontrolü
    new_achs = check_achievements(db_user, data)
    save_data(data)
    if new_achs:
        for ach in new_achs:
            await context.bot.send_message(
                chat_id=result.chat.id,
                text=f"🏆 {mention(user.id, user.first_name)} yeni bir başarı kazandı!\n"
                     f"{ach['emoji']} <b>{ach['name']}</b>\n"
                     f"_{ach['description']}_",
                parse_mode=ParseMode.HTML
            )

# ─────────────────────────────────────────────
#  MESAJ XP SİSTEMİ
# ─────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    text = update.message.text or ""
    cfg = load_config()
    data = load_data()

    db_user = get_user(data, user.id)
    db_user["username"] = user.username
    db_user["first_name"] = user.first_name
    db_user["messages"] += 1
    data["group_stats"]["total_messages"] += 1

    # Zararlı kelime filtresi
    lower_text = text.lower()
    for bad_word in cfg.get("banned_words", []):
        if bad_word in lower_text:
            try:
                await update.message.delete()
            except Exception:
                pass
            db_user["warnings"] += 1
            warn_count = db_user["warnings"]
            warn_msg = (
                f"⚠️ {mention(user.id, user.first_name)}, bu kelimeyi kullanamazsın!\n"
                f"Uyarı sayın: {warn_count}/{cfg['moderation']['max_warnings']}"
            )
            if warn_count >= cfg["moderation"]["max_warnings"]:
                try:
                    until = datetime.now() + timedelta(hours=cfg["moderation"]["mute_hours"])
                    await context.bot.restrict_chat_member(
                        chat_id=update.effective_chat.id,
                        user_id=user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until
                    )
                    warn_msg += f"\n🔇 {cfg['moderation']['mute_hours']} saat susturuldun!"
                    db_user["warnings"] = 0
                except Exception:
                    pass
            save_data(data)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=warn_msg,
                parse_mode=ParseMode.HTML
            )
            return

    # Spam koruması (aynı kişi 3 saniyede bir mesaj atabilir)
    now = datetime.now()
    last_time_str = db_user.get("last_message_time")
    if last_time_str:
        last_time = datetime.fromisoformat(last_time_str)
        if (now - last_time).total_seconds() < cfg["rewards"]["message_cooldown_seconds"]:
            save_data(data)
            return  # XP verme ama kaydet

    db_user["last_message_time"] = now.isoformat()

    # XP ver
    xp_gain = random.randint(
        cfg["rewards"]["message_xp_min"],
        cfg["rewards"]["message_xp_max"]
    )
    old_level = db_user["level"]
    db_user["xp"] += xp_gain
    db_user["total_xp_earned"] += xp_gain
    new_level = calculate_level(db_user["xp"])
    db_user["level"] = new_level

    # Selam algılama → bonus XP
    greet_words = cfg.get("greet_words", [])
    if any(word in lower_text for word in greet_words):
        bonus = cfg["rewards"]["greet_bonus_xp"]
        gold_bonus = cfg["rewards"]["greet_bonus_gold"]
        db_user["xp"] += bonus
        db_user["gold"] += gold_bonus
        db_user["total_xp_earned"] += bonus
        greeting_reply = random.choice(cfg["messages"]["greetings"])
        rank = get_rank_info(db_user["level"])
        await update.message.reply_text(
            f"{greeting_reply} {mention(user.id, user.first_name)}! 👋\n"
            f"⚡ <b>+{bonus} XP</b> ve <b>+{gold_bonus} 💰 Altın</b> kazandın!\n"
            f"🏅 Rankın: {rank['emoji']} <b>{rank['name']}</b>",
            parse_mode=ParseMode.HTML
        )

    # Seviye atladı mı?
    if new_level > old_level:
        rank = get_rank_info(new_level)
        level_up_msg = random.choice(cfg["messages"]["level_up"]).format(
            name=user.first_name, level=new_level
        )
        await update.message.reply_text(
            f"🎊 <b>SEVİYE ATLADI!</b>\n"
            f"{level_up_msg}\n\n"
            f"📈 Yeni Seviye: <b>{new_level}</b>\n"
            f"🏅 Yeni Rank: {rank['emoji']} <b>{rank['name']}</b>\n"
            f"💰 Bonus: <b>+{new_level * 50} Altın</b>",
            parse_mode=ParseMode.HTML
        )
        db_user["gold"] += new_level * 50

    # Başarı kontrolü
    new_achs = check_achievements(db_user, data)
    save_data(data)

    for ach in new_achs:
        await update.message.reply_text(
            f"🏆 {mention(user.id, user.first_name)} yeni başarı kazandı!\n"
            f"{ach['emoji']} <b>{ach['name']}</b>\n"
            f"_{ach['description']}_\n"
            f"Ödül: +{ach.get('reward_xp', 0)} XP, +{ach.get('reward_gold', 0)} 💰",
            parse_mode=ParseMode.HTML
        )

# ─────────────────────────────────────────────
#  KOMUTLAR
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Profilim", callback_data=f"profile_{update.effective_user.id}"),
         InlineKeyboardButton("🏆 Liderlik", callback_data="leaderboard_1")],
        [InlineKeyboardButton("🎮 Oyunlar", callback_data="games_menu"),
         InlineKeyboardButton("🎁 Günlük Bonus", callback_data="daily_bonus")],
        [InlineKeyboardButton("🏅 Başarılar", callback_data=f"achievements_{update.effective_user.id}"),
         InlineKeyboardButton("📖 Yardım", callback_data="help_menu")]
    ])
    await update.message.reply_text(
        f"🎮 <b>{cfg['bot_name']}</b> çevrimiçi!\n\n"
        f"Oyun stüdyosuna hoş geldin! Ben grubun yapay zeka asistanıyım.\n"
        f"Aşağıdaki menüden istediğin özelliğe ulaşabilirsin:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def cmd_profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    db_user = get_user(data, user.id)
    db_user["username"] = user.username
    db_user["first_name"] = user.first_name
    save_data(data)
    await show_profile(update, context, user.id, user.first_name)

async def show_profile(update_or_query, context, user_id: int, first_name: str):
    data = load_data()
    db_user = get_user(data, user_id)
    cfg = load_config()
    rank = get_rank_info(db_user["level"])

    level = db_user["level"]
    current_xp = db_user["xp"]
    next_xp = xp_for_level(level + 1) if level < 30 else current_xp
    xp_needed = next_xp - xp_for_level(level)
    xp_current = current_xp - xp_for_level(level)
    bar = progress_bar(xp_current, xp_needed, 12)

    title = db_user.get("title") or rank["name"]
    ach_count = len(db_user["achievements"])
    join_date = db_user.get("join_date", "?")[:10]

    trivia_rate = "0%"
    if db_user["trivia_total"] > 0:
        trivia_rate = f"{int(db_user['trivia_correct'] / db_user['trivia_total'] * 100)}%"

    msg = (
        f"╔══════════════════════════╗\n"
        f"║  👤 <b>{first_name[:16]}</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"🏅 <b>Rank:</b> {rank['emoji']} {rank['name']}\n"
        f"🎖 <b>Unvan:</b> {title}\n"
        f"📅 <b>Katılım:</b> {join_date}\n\n"
        f"━━━━━━ STATS ━━━━━━\n"
        f"⚡ <b>Seviye:</b> {level}/30\n"
        f"🔷 <b>XP:</b> {current_xp:,} / {next_xp:,}\n"
        f"   {bar} {int(xp_current/xp_needed*100) if xp_needed>0 else 100}%\n"
        f"💰 <b>Altın:</b> {db_user['gold']:,}\n"
        f"💬 <b>Mesaj:</b> {db_user['messages']:,}\n"
        f"🔥 <b>Streak:</b> {db_user['daily_streak']} gün\n"
        f"🏆 <b>Başarı:</b> {ach_count}/{len(cfg['achievements'])}\n"
        f"🎲 <b>Trivia:</b> {db_user['trivia_correct']}/{db_user['trivia_total']} ({trivia_rate})\n"
        f"⚠️ <b>Uyarı:</b> {db_user['warnings']}/{cfg['moderation']['max_warnings']}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏅 Başarılarım", callback_data=f"achievements_{user_id}"),
         InlineKeyboardButton("🎁 Günlük Bonus", callback_data="daily_bonus")],
        [InlineKeyboardButton("🏆 Liderlik Tablosu", callback_data="leaderboard_1")]
    ])

    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        await update_or_query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def cmd_liderlik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_leaderboard(update, context, page=1)

async def show_leaderboard(update_or_query, context, page: int = 1):
    data = load_data()
    cfg = load_config()
    per_page = 10
    users = [
        (uid, u) for uid, u in data["users"].items()
        if not u.get("is_banned", False) and u.get("messages", 0) > 0
    ]
    users.sort(key=lambda x: x[1]["xp"], reverse=True)

    total_pages = max(1, (len(users) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    page_users = users[start: start + per_page]

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 100
    msg = f"🏆 <b>ALTIN LİDERLİK TABLOSU</b> — Sayfa {page}/{total_pages}\n"
    msg += f"👥 Toplam oyuncu: {len(users)}\n\n"

    for i, (uid, u) in enumerate(page_users, start=start + 1):
        rank = get_rank_info(u["level"])
        name = u.get("first_name") or u.get("username") or "???"
        msg += (
            f"{medals[i-1]} <b>#{i}</b> {name[:14]}\n"
            f"   {rank['emoji']} Lv.{u['level']} | ⚡{u['xp']:,} XP | 💰{u['gold']:,}\n"
        )

    keyboard_buttons = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Önceki", callback_data=f"leaderboard_{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Sonraki ➡️", callback_data=f"leaderboard_{page+1}"))
    if nav:
        keyboard_buttons.append(nav)
    keyboard_buttons.append([InlineKeyboardButton("🔄 Yenile", callback_data=f"leaderboard_{page}")])

    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        await update_or_query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def cmd_gunluk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_daily_bonus(update, context, update.effective_user)

async def handle_daily_bonus(update_or_query, context, user):
    cfg = load_config()
    data = load_data()
    db_user = get_user(data, user.id)
    db_user["first_name"] = user.first_name

    now = datetime.now()
    last_daily = db_user.get("last_daily")

    if last_daily:
        last_dt = datetime.fromisoformat(last_daily)
        diff = now - last_dt
        if diff.total_seconds() < 86400:
            remaining = timedelta(seconds=86400) - diff
            h = int(remaining.total_seconds() // 3600)
            m = int((remaining.total_seconds() % 3600) // 60)
            msg = (
                f"⏰ Günlük bonusunu zaten aldın!\n"
                f"Kalan süre: <b>{h} saat {m} dakika</b>\n"
                f"🔥 Mevcut streak: {db_user['daily_streak']} gün"
            )
            if hasattr(update_or_query, "message") and update_or_query.message:
                await update_or_query.message.reply_text(msg, parse_mode=ParseMode.HTML)
            else:
                await update_or_query.answer(f"⏰ {h}s {m}dk sonra tekrar alabilirsin!", show_alert=True)
            return
        # Streak kontrolü
        if diff.total_seconds() < 172800:  # 48 saat içinde
            db_user["daily_streak"] += 1
        else:
            db_user["daily_streak"] = 1
    else:
        db_user["daily_streak"] = 1

    streak = db_user["daily_streak"]
    base_xp = cfg["rewards"]["daily_xp"]
    base_gold = cfg["rewards"]["daily_gold"]
    streak_bonus_xp = min(streak * cfg["rewards"]["streak_xp_per_day"], cfg["rewards"]["streak_max_xp"])
    streak_bonus_gold = min(streak * cfg["rewards"]["streak_gold_per_day"], cfg["rewards"]["streak_max_gold"])

    total_xp = base_xp + streak_bonus_xp
    total_gold = base_gold + streak_bonus_gold

    # Haftalık bonus
    weekly_bonus = ""
    if streak % 7 == 0:
        extra_xp = cfg["rewards"]["weekly_bonus_xp"]
        extra_gold = cfg["rewards"]["weekly_bonus_gold"]
        total_xp += extra_xp
        total_gold += extra_gold
        weekly_bonus = f"\n🎁 <b>HAFTALIK BONUS!</b> +{extra_xp} XP, +{extra_gold} 💰"

    db_user["xp"] += total_xp
    db_user["gold"] += total_gold
    db_user["total_xp_earned"] += total_xp
    db_user["last_daily"] = now.isoformat()

    old_level = db_user["level"]
    db_user["level"] = calculate_level(db_user["xp"])

    new_achs = check_achievements(db_user, data)
    save_data(data)

    streak_emoji = "🔥" * min(streak, 7)
    msg = (
        f"🎁 <b>GÜNLÜK BONUS ALINDI!</b>\n\n"
        f"⚡ XP: <b>+{base_xp}</b>"
        f"{'+ ' + str(streak_bonus_xp) + ' (streak)' if streak_bonus_xp > 0 else ''}\n"
        f"💰 Altın: <b>+{base_gold}</b>"
        f"{'+ ' + str(streak_bonus_gold) + ' (streak)' if streak_bonus_gold > 0 else ''}\n"
        f"{weekly_bonus}\n\n"
        f"🔥 Streak: <b>{streak} gün</b> {streak_emoji}\n"
        f"{'⬆️ SEVİYE ATLADIN! → ' + str(db_user['level']) if db_user['level'] > old_level else ''}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Profilimi Gör", callback_data=f"profile_{user.id}")]
    ])

    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        await update_or_query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    for ach in new_achs:
        chat_id = update_or_query.effective_chat.id if hasattr(update_or_query, "effective_chat") else update_or_query.message.chat_id
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🏆 {mention(user.id, user.first_name)} yeni başarı kazandı!\n"
                 f"{ach['emoji']} <b>{ach['name']}</b>\n_{ach['description']}_",
            parse_mode=ParseMode.HTML
        )

async def cmd_basarilar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    cfg = load_config()
    db_user = get_user(data, user.id)
    await show_achievements(update, context, user.id, user.first_name, db_user, cfg)

async def show_achievements(update_or_query, context, user_id, first_name, db_user, cfg):
    earned = db_user["achievements"]
    all_achs = cfg["achievements"]
    msg = f"🏆 <b>{first_name}'in Başarıları</b>\n"
    msg += f"Kazanılan: {len(earned)}/{len(all_achs)}\n\n"

    for ach in all_achs:
        if ach["id"] in earned:
            msg += f"✅ {ach['emoji']} <b>{ach['name']}</b>\n   _{ach['description']}_\n\n"
        else:
            msg += f"🔒 ??? <i>(Gizli başarı)</i>\n\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Profile Dön", callback_data=f"profile_{user_id}")]
    ])

    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        await update_or_query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)

# ─────────────────────────────────────────────
#  MİNİ OYUNLAR
# ─────────────────────────────────────────────

async def cmd_zar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zar at - bahis oyunu"""
    user = update.effective_user
    cfg = load_config()
    data = load_data()
    db_user = get_user(data, user.id)

    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "🎲 <b>Zar Oyunu</b>\nKullanım: /zar <miktar>\nÖrnek: /zar 100\n\n"
            "Sonuç 4-6 gelirse 1.5x kazanırsın!\nSonuç 1-3 gelirse kaybedersin!",
            parse_mode=ParseMode.HTML
        )
        return

    amount = int(args[0])
    if amount < 10:
        await update.message.reply_text("❌ Minimum bahis: 10 altın!")
        return
    if amount > db_user["gold"]:
        await update.message.reply_text(f"❌ Yeterli altının yok! Mevcut: {db_user['gold']} 💰")
        return
    if amount > cfg["games"]["dice_max_bet"]:
        await update.message.reply_text(f"❌ Maksimum bahis: {cfg['games']['dice_max_bet']} altın!")
        return

    dice_msg = await update.message.reply_dice(emoji="🎲")
    await asyncio.sleep(4)

    result = dice_msg.dice.value
    if result >= 4:
        won = int(amount * 1.5)
        db_user["gold"] += won
        outcome = f"✅ <b>KAZANDIN!</b> +{won} 💰"
    else:
        db_user["gold"] -= amount
        outcome = f"❌ <b>KAYBETTİN!</b> -{amount} 💰"

    save_data(data)
    await update.message.reply_text(
        f"🎲 Zar: <b>{result}</b>\n{outcome}\n💰 Bakiye: {db_user['gold']:,}",
        parse_mode=ParseMode.HTML
    )

async def cmd_yazi_tura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yazı-Tura oyunu"""
    user = update.effective_user
    cfg = load_config()
    data = load_data()
    db_user = get_user(data, user.id)

    args = context.args
    if len(args) < 2 or not args[1].isdigit():
        await update.message.reply_text(
            "🪙 <b>Yazı-Tura</b>\nKullanım: /yatura <yazi/tura> <miktar>\nÖrnek: /yatura yazi 200",
            parse_mode=ParseMode.HTML
        )
        return

    choice = args[0].lower()
    if choice not in ["yazi", "tura"]:
        await update.message.reply_text("❌ yazi veya tura gir!")
        return

    amount = int(args[1])
    if amount < 10 or amount > db_user["gold"]:
        await update.message.reply_text("❌ Geçersiz miktar!")
        return

    result = random.choice(["yazi", "tura"])
    emoji = "📝" if result == "yazi" else "👑"

    if result == choice:
        db_user["gold"] += amount
        outcome = f"✅ <b>KAZANDIN!</b> +{amount} 💰"
    else:
        db_user["gold"] -= amount
        outcome = f"❌ <b>KAYBETTİN!</b> -{amount} 💰"

    save_data(data)
    await update.message.reply_text(
        f"{emoji} Sonuç: <b>{result.upper()}</b>\n{outcome}\n💰 Bakiye: {db_user['gold']:,}",
        parse_mode=ParseMode.HTML
    )

# Trivia sistemi
trivia_sessions = {}

async def cmd_trivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trivia sorusu sor"""
    cfg = load_config()
    question = random.choice(cfg["trivia_questions"])
    chat_id = update.effective_chat.id

    # Shuffle answers
    answers = question["wrong_answers"] + [question["answer"]]
    random.shuffle(answers)

    correct_idx = answers.index(question["answer"])
    trivia_sessions[chat_id] = {
        "question_id": question["id"],
        "correct_answer": question["answer"],
        "correct_index": correct_idx,
        "asked_by": update.effective_user.id,
        "answered_by": [],
        "expires": (datetime.now() + timedelta(seconds=30)).isoformat()
    }

    buttons = [
        [InlineKeyboardButton(f"{['A', 'B', 'C', 'D'][i]}) {ans}", callback_data=f"trivia_{i}")]
        for i, ans in enumerate(answers)
    ]

    await update.message.reply_text(
        f"🧠 <b>TRİVİA SORUSU</b>\n"
        f"Kategori: {question.get('category', 'Genel')}\n\n"
        f"❓ {question['question']}\n\n"
        f"⏳ 30 saniyeniz var!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def cmd_unvan_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı unvan seçer"""
    cfg = load_config()
    data = load_data()
    user = update.effective_user
    db_user = get_user(data, user.id)

    available_titles = [t for t in cfg["titles"] if db_user["level"] >= t["min_level"]]

    if not context.args:
        titles_text = "\n".join([
            f"{'✅' if db_user['title'] == t['name'] else '🏷'} {t['name']} (Lv.{t['min_level']}+)"
            for t in available_titles
        ])
        await update.message.reply_text(
            f"🏷 <b>Kullanılabilir Unvanlar</b>\n\n{titles_text}\n\n"
            f"Seçmek için: /unvan <unvan adı>",
            parse_mode=ParseMode.HTML
        )
        return

    title_name = " ".join(context.args)
    matching = [t for t in available_titles if t["name"].lower() == title_name.lower()]
    if not matching:
        await update.message.reply_text("❌ Böyle bir unvan yok veya seviyeniz yeterli değil!")
        return

    db_user["title"] = matching[0]["name"]
    save_data(data)
    await update.message.reply_text(f"✅ Unvanın <b>{matching[0]['name']}</b> olarak güncellendi!", parse_mode=ParseMode.HTML)

async def cmd_hediye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Birine altın gönder"""
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Altın göndermek için bir mesaja yanıtla!")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Kullanım: /hediye <miktar> (bir mesajı yanıtlayarak)")
        return

    sender = update.effective_user
    receiver = update.message.reply_to_message.from_user
    amount = int(context.args[0])

    if receiver.id == sender.id:
        await update.message.reply_text("❌ Kendine hediye gönderemezsin!")
        return
    if amount < 1:
        await update.message.reply_text("❌ Geçersiz miktar!")
        return

    data = load_data()
    sender_db = get_user(data, sender.id)
    receiver_db = get_user(data, receiver.id)

    if sender_db["gold"] < amount:
        await update.message.reply_text(f"❌ Yeterli altının yok! Mevcut: {sender_db['gold']} 💰")
        return

    sender_db["gold"] -= amount
    receiver_db["gold"] += amount
    save_data(data)

    await update.message.reply_text(
        f"🎁 {mention(sender.id, sender.first_name)} → {mention(receiver.id, receiver.first_name)}\n"
        f"💰 <b>{amount} altın</b> gönderildi!\n\n"
        f"Gönderen bakiye: {sender_db['gold']:,}\n"
        f"Alan bakiye: {receiver_db['gold']:,}",
        parse_mode=ParseMode.HTML
    )

async def cmd_istatistik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grup istatistiklerini göster"""
    data = load_data()
    cfg = load_config()
    stats = data.get("group_stats", {})
    users = data["users"]

    active_users = [u for u in users.values() if u.get("messages", 0) > 0]
    total_xp = sum(u.get("xp", 0) for u in active_users)
    total_gold = sum(u.get("gold", 0) for u in active_users)
    max_level_user = max(active_users, key=lambda u: u["level"]) if active_users else None
    top_name = max_level_user.get("first_name", "???") if max_level_user else "?"

    await update.message.reply_text(
        f"📊 <b>GRUP İSTATİSTİKLERİ</b>\n\n"
        f"👥 Toplam üye: {len(users)}\n"
        f"✅ Aktif üye: {len(active_users)}\n"
        f"💬 Toplam mesaj: {stats.get('total_messages', 0):,}\n"
        f"⚡ Toplam XP: {total_xp:,}\n"
        f"💰 Toplam altın: {total_gold:,}\n"
        f"👑 En yüksek seviye: {top_name} (Lv.{max_level_user['level'] if max_level_user else 0})\n"
        f"🤖 Bot: {cfg['bot_name']}",
        parse_mode=ParseMode.HTML
    )

async def cmd_yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Profil", callback_data=f"profile_{update.effective_user.id}"),
         InlineKeyboardButton("🏆 Liderlik", callback_data="leaderboard_1")],
        [InlineKeyboardButton("🎲 Oyunlar", callback_data="games_menu")]
    ])
    await update.message.reply_text(
        "📖 <b>KOMUT LİSTESİ</b>\n\n"
        "👤 <b>Profil & Puan</b>\n"
        "/profil — Profilini gör\n"
        "/liderlik — Liderlik tablosu\n"
        "/gunluk — Günlük bonus al\n"
        "/basarilar — Başarılarını gör\n"
        "/istatistik — Grup stats\n"
        "/unvan — Unvan değiştir\n\n"
        "🎮 <b>Oyunlar</b>\n"
        "/zar <miktar> — Zar bahis oyunu\n"
        "/yatura <yazi/tura> <miktar> — Yazı-tura\n"
        "/trivia — Bilgi yarışması sorusu\n\n"
        "💰 <b>Ekonomi</b>\n"
        "/hediye <miktar> — Birine altın gönder\n\n"
        "🤖 <b>Yapay Zeka</b>\n"
        "/sorusor <soru> — Tek seferlik soru sor\n"
        "/aisohbet <mesaj> — Bağlam hatırlayan sohbet\n"
        "/aisifirla — Konuşma geçmişini sıfırla\n\n"
        "ℹ️ Bot selam mesajlarına +XP ve altın verir!\n"
        "🔥 Her gün giriş yap, streak bonusu kazan!",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

# ─────────────────────────────────────────────
#  MODERASYon KOMUTLARI (sadece adminler)
# ─────────────────────────────────────────────

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    member = await context.bot.get_chat_member(update.effective_chat.id, user.id)
    return member.status in ["administrator", "creator"]

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Bir mesajı yanıtla!")
        return
    target = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "Sebep belirtilmedi"
    data = load_data()
    db_user = get_user(data, target.id)
    db_user["is_banned"] = True
    save_data(data)
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(
            f"🔨 {mention(target.id, target.first_name)} banlandı!\n📝 Sebep: {reason}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

async def cmd_uyari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Bir mesajı yanıtla!")
        return
    target = update.message.reply_to_message.from_user
    cfg = load_config()
    data = load_data()
    db_user = get_user(data, target.id)
    db_user["warnings"] += 1
    warn_count = db_user["warnings"]
    save_data(data)

    if warn_count >= cfg["moderation"]["max_warnings"]:
        until = datetime.now() + timedelta(hours=cfg["moderation"]["mute_hours"])
        try:
            await context.bot.restrict_chat_member(
                update.effective_chat.id, target.id,
                ChatPermissions(can_send_messages=False), until_date=until
            )
            db_user["warnings"] = 0
            save_data(data)
            await update.message.reply_text(
                f"🔇 {mention(target.id, target.first_name)} {cfg['moderation']['mute_hours']} saat susturuldu!",
                parse_mode=ParseMode.HTML
            )
            return
        except Exception:
            pass

    await update.message.reply_text(
        f"⚠️ {mention(target.id, target.first_name)} uyarıldı!\n"
        f"Uyarı: {warn_count}/{cfg['moderation']['max_warnings']}",
        parse_mode=ParseMode.HTML
    )

async def cmd_xp_ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin XP ver"""
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text("❌ Kullanım: /xpver <miktar> (mesajı yanıtla)")
        return
    target = update.message.reply_to_message.from_user
    amount = int(context.args[0])
    data = load_data()
    db_user = get_user(data, target.id)
    db_user["xp"] += amount
    db_user["total_xp_earned"] += amount
    db_user["level"] = calculate_level(db_user["xp"])
    save_data(data)
    await update.message.reply_text(
        f"✅ {mention(target.id, target.first_name)} → +{amount} XP verildi!",
        parse_mode=ParseMode.HTML
    )

# ─────────────────────────────────────────────
#  CALLBACK HANDLER (inline butonlar)
# ─────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data_str = query.data
    user = query.from_user
    cfg = load_config()

    if data_str.startswith("profile_"):
        uid = int(data_str.split("_")[1])
        data = load_data()
        db_user = get_user(data, uid)
        fname = db_user.get("first_name") or "Oyuncu"
        await show_profile(query, context, uid, fname)

    elif data_str.startswith("leaderboard_"):
        page = int(data_str.split("_")[1])
        await show_leaderboard(query, context, page)

    elif data_str == "daily_bonus":
        await handle_daily_bonus(query, context, user)

    elif data_str.startswith("achievements_"):
        uid = int(data_str.split("_")[1])
        data = load_data()
        db_user = get_user(data, uid)
        fname = db_user.get("first_name") or "Oyuncu"
        await show_achievements(query, context, uid, fname, db_user, cfg)

    elif data_str == "games_menu":
        await query.edit_message_text(
            "🎮 <b>OYUN MENÜSÜ</b>\n\n"
            "🎲 /zar <miktar> — Zar at, bahis yap!\n"
            "🪙 /yatura <seçim> <miktar> — Yazı-tura\n"
            "🧠 /trivia — Bilgi sorusu\n\n"
            "💡 <i>Oyunlarda altın kazan veya kaybet!</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Geri", callback_data="help_menu")]
            ])
        )

    elif data_str == "help_menu":
        await query.edit_message_text(
            "📖 <b>YARDIM MENÜSÜ</b>\n\n"
            "Tüm komutlar için /yardim yaz!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Profilim", callback_data=f"profile_{user.id}"),
                 InlineKeyboardButton("🏆 Liderlik", callback_data="leaderboard_1")]
            ])
        )

    elif data_str.startswith("trivia_"):
        chat_id = query.message.chat_id
        session = trivia_sessions.get(chat_id)

        if not session:
            await query.answer("❌ Bu soru süresi doldu!", show_alert=True)
            return
        if user.id in session["answered_by"]:
            await query.answer("❌ Bu soruyu zaten cevapladın!", show_alert=True)
            return
        if datetime.now() > datetime.fromisoformat(session["expires"]):
            await query.answer("⏰ Süre doldu!", show_alert=True)
            trivia_sessions.pop(chat_id, None)
            return

        chosen_idx = int(data_str.split("_")[1])
        session["answered_by"].append(user.id)
        data = load_data()
        db_user = get_user(data, user.id)
        db_user["trivia_total"] += 1

        if chosen_idx == session["correct_index"]:
            xp_reward = cfg["rewards"]["trivia_correct_xp"]
            gold_reward = cfg["rewards"]["trivia_correct_gold"]
            db_user["xp"] += xp_reward
            db_user["gold"] += gold_reward
            db_user["trivia_correct"] += 1
            db_user["total_xp_earned"] += xp_reward
            db_user["level"] = calculate_level(db_user["xp"])
            check_achievements(db_user, data)
            save_data(data)
            await query.answer(f"✅ DOĞRU! +{xp_reward} XP +{gold_reward} 💰", show_alert=True)
            await query.edit_message_text(
                f"✅ <b>{user.first_name}</b> doğru cevapladı!\n"
                f"Cevap: <b>{session['correct_answer']}</b>\n"
                f"Ödül: +{xp_reward} XP, +{gold_reward} 💰",
                parse_mode=ParseMode.HTML
            )
            trivia_sessions.pop(chat_id, None)
        else:
            db_user["xp"] = max(0, db_user["xp"] - cfg["rewards"]["trivia_wrong_xp_penalty"])
            save_data(data)
            await query.answer(f"❌ YANLIŞ! -{cfg['rewards']['trivia_wrong_xp_penalty']} XP", show_alert=True)

# ─────────────────────────────────────────────
#  HATA YÖNETİCİSİ
# ─────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Hata: {context.error}", exc_info=context.error)


# ─────────────────────────────────────────────
#  YAPAY ZEKA KOMUTLARI
# ─────────────────────────────────────────────

# Konuşma geçmişini tut (kullanıcı bazlı)
ai_conversations = {}

async def cmd_sorusor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yapay zekaya soru sor - /sorusor <soru>"""
    cfg = load_config()
    groq_key = cfg.get("groq_api_key")

    import os
    env_key = os.environ.get("GROQ_API_KEY")
    if env_key:
        groq_key = env_key

    if not groq_key or groq_key == "YOUR_GROQ_API_KEY_HERE":
        await update.message.reply_text(
            "❌ Groq API key ayarlanmamış!\n"
            "config.json içine \"groq_api_key\" ekle."
        )
        return

    if not GROQ_AVAILABLE:
        await update.message.reply_text("❌ groq kütüphanesi yüklü değil!")
        return

    user = update.effective_user
    soru = " ".join(context.args) if context.args else ""

    if not soru:
        await update.message.reply_text(
            "🤖 <b>Yapay Zeka Asistanı</b>\n\n"
            "Kullanım: /sorusor <sorunuz>\n"
            "Örnek: /sorusor Unity'de nasıl oyun yapılır?\n\n"
            "💬 /aisohbet — Sürekli sohbet modunu başlat\n"
            "🗑 /aisifirla — Konuşma geçmişini sıfırla",
            parse_mode=ParseMode.HTML
        )
        return

    # Yazıyor... göster
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    # XP ver
    data = load_data()
    db_user = get_user(data, user.id)
    db_user["xp"] += 5
    db_user["total_xp_earned"] += 5
    db_user["commands_used"] += 1
    save_data(data)

    try:
        client = GroqClient(api_key=groq_key)

        # Sistem promptu - oyun stüdyosu temalı
        system_prompt = cfg.get("ai_system_prompt",
            "Sen Ti App Studio'nun Telegram grup asistanısın. "
            "Oyun geliştirme, programlama, Unity, Unreal Engine, "
            "game design ve genel konularda yardımcı olursun. "
            "Türkçe cevap verirsin. Kısa ve net cevaplar verirsin. "
            "Samimi ve enerjik bir tonsun. Emoji kullanabilirsin."
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": soru}
            ],
            max_tokens=1024,
            temperature=0.7,
        )

        cevap = response.choices[0].message.content

        # Çok uzunsa böl
        if len(cevap) > 4000:
            cevap = cevap[:4000] + "...\n\n_(Cevap kısaltıldı)_"

        await update.message.reply_text(
            f"🤖 <b>Yapay Zeka Cevabı:</b>\n\n{cevap}\n\n"
            f"<i>⚡ +5 XP kazandın!</i>",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"Groq API hatası: {e}")
        await update.message.reply_text(
            "❌ Yapay zeka şu an cevap veremiyor, lütfen tekrar dene!\n"
            f"Hata: {str(e)[:100]}"
        )


async def cmd_aisohbet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Çok turlu AI sohbet - bağlam hatırlar"""
    cfg = load_config()
    groq_key = cfg.get("groq_api_key")

    import os
    env_key = os.environ.get("GROQ_API_KEY")
    if env_key:
        groq_key = env_key

    if not groq_key or groq_key == "YOUR_GROQ_API_KEY_HERE":
        await update.message.reply_text("❌ Groq API key ayarlanmamış!")
        return

    user = update.effective_user
    mesaj = " ".join(context.args) if context.args else ""

    if not mesaj:
        uid = str(user.id)
        history_len = len(ai_conversations.get(uid, []))
        await update.message.reply_text(
            f"💬 <b>AI Sohbet Modu</b>\n\n"
            f"Ben konuşma geçmişini hatırlıyorum!\n"
            f"Mevcut geçmiş: {history_len // 2} mesaj\n\n"
            f"Kullanım: /aisohbet <mesajın>\n"
            f"🗑 Sıfırlamak için: /aisifirla",
            parse_mode=ParseMode.HTML
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    uid = str(user.id)
    if uid not in ai_conversations:
        ai_conversations[uid] = []

    # Geçmişe ekle
    ai_conversations[uid].append({"role": "user", "content": mesaj})

    # Son 10 mesajı tut (hafıza limiti)
    if len(ai_conversations[uid]) > 20:
        ai_conversations[uid] = ai_conversations[uid][-20:]

    cfg = load_config()
    system_prompt = cfg.get("ai_system_prompt",
        "Sen Ti App Studio'nun Telegram grup asistanısın. "
        "Oyun geliştirme, programlama ve genel konularda yardımcı olursun. "
        "Türkçe konuşursun. Samimi ve enerjiksin."
    )

    try:
        client = GroqClient(api_key=groq_key)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(ai_conversations[uid])

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        cevap = response.choices[0].message.content
        ai_conversations[uid].append({"role": "assistant", "content": cevap})

        if len(cevap) > 4000:
            cevap = cevap[:4000] + "..."

        turno = len(ai_conversations[uid]) // 2
        await update.message.reply_text(
            f"🤖 <b>AI</b> (#{turno}):\n\n{cevap}",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"Groq sohbet hatası: {e}")
        await update.message.reply_text("❌ Hata oluştu, tekrar dene!")


async def cmd_aisifirla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Konuşma geçmişini sıfırla"""
    uid = str(update.effective_user.id)
    if uid in ai_conversations:
        del ai_conversations[uid]
    await update.message.reply_text(
        "🗑 Konuşma geçmişin sıfırlandı! Yeni bir sohbet başlatabilirsin."
    )


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
#  RENDER.COM UYKU ENGELI (Keep-Alive Server)
# ─────────────────────────────────────────────
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot aktif!")
    def log_message(self, *args):
        pass

def keep_alive():
    server = HTTPServer(("0.0.0.0", 8080), PingHandler)
    server.serve_forever()

def main():
    cfg = load_config()
    token = cfg["bot_token"]

    # Render.com Environment Variable desteği
    import os
    env_token = os.environ.get("BOT_TOKEN")
    if env_token:
        token = env_token

    if token in ("YOUR_BOT_TOKEN_HERE", "ENV", "", None):
        print("❌ HATA: config.json içindeki bot_token'ı güncelle!")
        print("   @BotFather'dan token al ve config.json'a yapıştır.")
        return

    # Proxy ayarı (Türkiye'de Telegram engeliyse kullan)
    # config.json'a ekle: "proxy": "socks5://127.0.0.1:9050"
    proxy_url = cfg.get("proxy", None)

    from telegram.request import HTTPXRequest
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
        proxy=proxy_url,
    )

    app = Application.builder().token(token).request(request).build()

    # Komut handler'ları
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("yardim", cmd_yardim))
    app.add_handler(CommandHandler("profil", cmd_profil))
    app.add_handler(CommandHandler("liderlik", cmd_liderlik))
    app.add_handler(CommandHandler("gunluk", cmd_gunluk))
    app.add_handler(CommandHandler("basarilar", cmd_basarilar))
    app.add_handler(CommandHandler("zar", cmd_zar))
    app.add_handler(CommandHandler("yatura", cmd_yazi_tura))
    app.add_handler(CommandHandler("trivia", cmd_trivia))
    app.add_handler(CommandHandler("unvan", cmd_unvan_sec))
    app.add_handler(CommandHandler("hediye", cmd_hediye))
    app.add_handler(CommandHandler("istatistik", cmd_istatistik))

    app.add_handler(CommandHandler("sorusor", cmd_sorusor))
    app.add_handler(CommandHandler("aisohbet", cmd_aisohbet))
    app.add_handler(CommandHandler("aisifirla", cmd_aisifirla))

    # Admin komutları
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("uyari", cmd_uyari))
    app.add_handler(CommandHandler("xpver", cmd_xp_ver))

    # Yeni üye handler
    app.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))

    # Mesaj handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Callback handler
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Hata handler
    app.add_error_handler(error_handler)

    print(f"🚀 {cfg['bot_name']} başlatıldı!")
    print("📌 Durdurmak için Ctrl+C")
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
