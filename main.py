import telebot
from telebot import types
import sqlite3
from datetime import datetime

# Конфигурация
BOT_TOKEN = "8984814572:AAGPyC1TnACYBizhvGX3ejF2Yjl96kgOv8Y"
ADMIN_ID = 5176998143

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица сообщений для диалога
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER,
            to_user_id INTEGER,
            message_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Таблица статусов диалогов (открыт/закрыт)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dialog_status (
            user_id INTEGER PRIMARY KEY,
            is_open BOOLEAN DEFAULT FALSE,
            opened_at TIMESTAMP,
            closed_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Работа с базой данных
def add_user(user_id, username, first_name, last_name=None):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, first_name, last_name, registered_at FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

def get_user_by_id(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, first_name, last_name FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def open_dialog(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO dialog_status (user_id, is_open, opened_at)
        VALUES (?, TRUE, ?)
    ''', (user_id, datetime.now()))
    conn.commit()
    conn.close()

def close_dialog(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE dialog_status SET is_open = FALSE, closed_at = ?
        WHERE user_id = ?
    ''', (datetime.now(), user_id))
    conn.commit()
    conn.close()

def is_dialog_open(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_open FROM dialog_status WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0]

def save_message(from_user_id, to_user_id, message_text):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (from_user_id, to_user_id, message_text)
        VALUES (?, ?, ?)
    ''', (from_user_id, to_user_id, message_text))
    conn.commit()
    conn.close()

def get_unread_messages(to_user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT from_user_id, message_text, timestamp FROM messages 
        WHERE to_user_id = ? AND is_read = FALSE
        ORDER BY timestamp
    ''', (to_user_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages

def mark_messages_as_read(to_user_id, from_user_id=None):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    if from_user_id:
        cursor.execute('''
            UPDATE messages SET is_read = TRUE 
            WHERE to_user_id = ? AND from_user_id = ?
        ''', (to_user_id, from_user_id))
    else:
        cursor.execute('''
            UPDATE messages SET is_read = TRUE WHERE to_user_id = ?
        ''', (to_user_id,))
    conn.commit()
    conn.close()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_feedback = types.KeyboardButton("📝 Оставить отзыв")
    btn_help = types.KeyboardButton("❓ Попросить помощь")
    markup.add(btn_feedback, btn_help)
    
    bot.send_message(
        message.chat.id,
        f"Привет, {user.first_name}! 👋\n\n"
        "Я бот для обратной связи и помощи.\n"
        "Выберите действие:",
        reply_markup=markup
    )

# Обработчик кнопки "Оставить отзыв"
@bot.message_handler(func=lambda message: message.text == "📝 Оставить отзыв")
def feedback_request(message):
    bot.send_message(
        message.chat.id,
        "Пожалуйста, напишите ваш отзыв. Я передам его администрации."
    )
    bot.register_next_step_handler(message, process_feedback)

def process_feedback(message):
    feedback_text = message.text
    
    # Сохраняем сообщение
    save_message(message.from_user.id, ADMIN_ID, f"📝 ОТЗЫВ:\n{feedback_text}")
    
    bot.send_message(
        message.chat.id,
        "✅ Ваш отзыв отправлен администрации!\n\n"
        "Если вам понадобится ещё что-то, выберите действие в меню."
    )
    
    # Уведомляем админа
    try:
        bot.send_message(
            ADMIN_ID,
            f"📬 Новый отзыв от пользователя!\n"
            f"👤 Пользователь: @{message.from_user.username or 'без username'} ({message.from_user.first_name})\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"📝 Текст:\n{feedback_text}",
            reply_markup=get_user_action_markup(message.from_user.id)
        )
    except:
        pass

# Обработчик кнопки "Попросить помощь"
@bot.message_handler(func=lambda message: message.text == "❓ Попросить помощь")
def help_request(message):
    bot.send_message(
        message.chat.id,
        "Опишите вашу проблему или вопрос. Администрация скоро ответит."
    )
    bot.register_next_step_handler(message, process_help_request)

def process_help_request(message):
    help_text = message.text
    
    # Сохраняем сообщение
    save_message(message.from_user.id, ADMIN_ID, f"❓ ПОМОЩЬ:\n{help_text}")
    
    bot.send_message(
        message.chat.id,
        "✅ Ваш запрос отправлен администрации!\n"
        "Ожидайте ответа."
    )
    
    # Уведомляем админа
    try:
        bot.send_message(
            ADMIN_ID,
            f"🆘 Запрос помощи от пользователя!\n"
            f"👤 Пользователь: @{message.from_user.username or 'без username'} ({message.from_user.first_name})\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"❓ Вопрос:\n{help_text}",
            reply_markup=get_user_action_markup(message.from_user.id)
        )
    except:
        pass

# Клавиатура действий для админа
def get_user_action_markup(user_id):
    markup = types.InlineKeyboardMarkup()
    btn_dialog = types.InlineKeyboardButton("💬 Начать диалог", callback_data=f"dialog_{user_id}")
    btn_info = types.InlineKeyboardButton("ℹ️ Инфо", callback_data=f"info_{user_id}")
    markup.add(btn_dialog, btn_info)
    return markup

# Клавиатура управления диалогом
def get_dialog_control_markup(user_id):
    markup = types.InlineKeyboardMarkup()
    btn_close = types.InlineKeyboardButton("❌ Закрыть диалог", callback_data=f"close_{user_id}")
    btn_back = types.InlineKeyboardButton("🔙 Назад к списку", callback_data="user_list")
    markup.add(btn_close, btn_back)
    return markup

# Обработчик команды /admin для админа
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Доступ запрещён. Только для администратора.")
        return
    
    users = get_all_users()
    
    if not users:
        bot.send_message(message.chat.id, "📭 Пока нет зарегистрированных пользователей.")
        return
    
    markup = types.InlineKeyboardMarkup()
    
    for user in users:
        user_id, username, first_name, last_name, registered = user
        display_name = first_name + (f" {last_name}" if last_name else "")
        username_str = f"@{username}" if username else ""
        btn_text = f"{display_name} {username_str}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"user_{user_id}"))
    
    bot.send_message(
        message.chat.id,
        f"👥 Список пользователей ({len(users)}):\n\nВыберите пользователя:",
        reply_markup=markup
    )

# Обработчик инлайн-кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    data = call.data
    
    # Список всех пользователей
    if data == "user_list":
        users = get_all_users()
        markup = types.InlineKeyboardMarkup()
        for user in users:
            user_id, username, first_name, last_name, registered = user
            display_name = first_name + (f" {last_name}" if last_name else "")
            username_str = f"@{username}" if username else ""
            btn_text = f"{display_name} {username_str}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"user_{user_id}"))
        
        bot.edit_message_text(
            "👥 Список пользователей:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    # Информация о пользователе
    elif data.startswith("info_"):
        user_id = int(data.split("_")[1])
        user = get_user_by_id(user_id)
        if user:
            user_id, username, first_name, last_name = user
            dialog_status = "🟢 Открыт" if is_dialog_open(user_id) else "🔴 Закрыт"
            
            info_text = (
                f"ℹ️ Информация о пользователе:\n\n"
                f"👤 Имя: {first_name} {last_name or ''}\n"
                f"📱 Username: @{username or 'нет'}\n"
                f"🆔 ID: {user_id}\n"
                f"💬 Статус диалога: {dialog_status}"
            )
            
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("🔙 Назад", callback_data="user_list")
            btn_dialog = types.InlineKeyboardButton("💬 Диалог", callback_data=f"dialog_{user_id}")
            markup.add(btn_dialog, btn_back)
            
            bot.edit_message_text(info_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    # Начало диалога с пользователем
    elif data.startswith("dialog_"):
        user_id = int(data.split("_")[1])
        user = get_user_by_id(user_id)
        
        if user:
            open_dialog(user_id)
            user_name = f"{user[1]} ({user[2]})"
            
            bot.edit_message_text(
                f"💬 Диалог с пользователем: {user_name}\n"
                f"🆔 ID: {user_id}\n\n"
                f"Статус: 🟢 Открыт\n\n"
                f"Теперь все ваши сообщения будут отправляться этому пользователю.\n"
                f"Напишите сообщение ниже или закройте диалог.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_dialog_control_markup(user_id)
            )
            
            # Сохраняем текущий диалог в состоянии (для обработки следующих сообщений)
            bot.set_chat_administrator_can_post(call.message.chat.id, True)
            
            # Отправляем уведомление пользователю
            try:
                bot.send_message(
                    user_id,
                    "🔔 Администрация начала с вами диалог!\n"
                    "Теперь вы можете общаться напрямую.\n"
                    "Просто напишите сообщение."
                )
            except:
                pass
    
    # Закрытие диалога
    elif data.startswith("close_"):
        user_id = int(data.split("_")[1])
        user = get_user_by_id(user_id)
        
        close_dialog(user_id)
        
        if user:
            bot.edit_message_text(
                f"❌ Диалог с пользователем {user[2]} закрыт.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_user_action_markup(user_id)
            )
            
            # Уведомляем пользователя
            try:
                bot.send_message(
                    user_id,
                    "🔒 Администрация закрыла диалог.\n"
                    "Если у вас возникнут ещё вопросы, обратитесь снова."
                )
            except:
                pass

# Обработка сообщений от админа во время диалога
@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID)
def admin_message_handler(message):
    # Проверяем, есть ли активные диалоги
    # Для простоты - если сообщение не команда и не ответ на callback
    if message.text and not message.text.startswith('/'):
        # Получаем все открытые диалоги
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM dialog_status WHERE is_open = TRUE')
        open_dialogs = cursor.fetchall()
        conn.close()
        
        if open_dialogs:
            # Отправляем сообщение всем пользователям с открытым диалогом
            for (user_id,) in open_dialogs:
                try:
                    save_message(ADMIN_ID, user_id, message.text)
                    bot.send_message(
                        user_id,
                        f"💬 Сообщение от администрации:\n\n{message.text}"
                    )
                except Exception as e:
                    print(f"Ошибка отправки пользователю {user_id}: {e}")
            
            bot.reply_to(message, f"✅ Сообщение отправлено {len(open_dialogs)} пользователю(ям)")
        else:
            bot.reply_to(message, "❌ Нет активных диалогов. Выберите пользователя через /admin")

# Обработка сообщений от пользователей во время диалога
@bot.message_handler(func=lambda message: message.from_user.id != ADMIN_ID and is_dialog_open(message.from_user.id))
def user_dialog_message(message):
    user_id = message.from_user.id
    
    # Сохраняем и пересылаем сообщение админу
    save_message(user_id, ADMIN_ID, message.text)
    
    try:
        bot.send_message(
            ADMIN_ID,
            f"💬 Сообщение от пользователя:\n"
            f"👤 {message.from_user.first_name} (ID: {user_id})\n"
            f"📝 Текст:\n{message.text}",
            reply_markup=get_dialog_control_markup(user_id)
        )
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

# Запуск бота
if __name__ == "__main__":
    init_db()
    print("Бот запущен...")
    bot.infinity_polling()
