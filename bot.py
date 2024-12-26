import os
import re
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import datetime
from dotenv import load_dotenv  # Thêm dòng này
# Thay thế bằng Token Bot mới của bạn
load_dotenv()  # Thêm dòng này để tải biến môi trường từ .env

# Lấy Token từ biến môi trường
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")

# Biến để lưu trữ thông tin người dùng
user_data = {}

# Lệnh thiết lập Sheet ID
async def set_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheet_id = ' '.join(context.args).strip()
    if not sheet_id:
        await update.message.reply_text("Vui lòng cung cấp Sheet ID. Ví dụ: /sheet YOUR_SHEET_ID")
        return
    chat_id = update.effective_chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]['sheet_id'] = sheet_id
    await update.message.reply_text(f"✅ Sheet ID đã được lưu: {sheet_id}")

# Lệnh thiết lập Service Account File
async def set_service_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service_account_file = ' '.join(context.args).strip()
    if not service_account_file:
        await update.message.reply_text(
            "❌ Vui lòng cung cấp đường dẫn đến tệp service account JSON.\n"
            "Ví dụ: /setserviceaccount path/to/service_account.json\n"
            "Nếu bạn chưa có Service Account, hãy xem hướng dẫn tại /instructions."
        )
        return
    chat_id = update.effective_chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]['service_account_file'] = service_account_file
    await update.message.reply_text("✅ Đường dẫn đến tệp service account đã được lưu.")

# Lệnh hướng dẫn lấy Service Account
async def instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instructions_message = (
        "📄 **Hướng Dẫn Tạo và Thiết Lập Service Account cho Google Sheets API** 📄\n\n"
        "Để bot có thể ghi dữ liệu vào Google Sheets, bạn cần tạo một **Service Account** và chia sẻ Google Sheet với Service Account đó. Vui lòng làm theo các bước dưới đây:\n\n"
        "1. **Tạo Project trên Google Cloud Console:**\n"
        "   - Truy cập [Google Cloud Console](https://console.cloud.google.com/).\n"
        "   - Tạo một Project mới hoặc sử dụng Project hiện có.\n\n"
        "2. **Bật Google Sheets API:**\n"
        "   - Vào **APIs & Services** > **Library**.\n"
        "   - Tìm kiếm **Google Sheets API** và nhấn **Enable**.\n\n"
        "3. **Tạo Service Account và Tải xuống Key:**\n"
        "   - Trong **APIs & Services** > **Credentials**, nhấn **Create Credentials** > **Service account**.\n"
        "   - Điền thông tin cần thiết và tạo Service Account.\n"
        "   - Sau khi tạo, vào **Manage keys** và nhấn **Add Key** > **Create new key** > **JSON**. Tệp JSON sẽ được tải xuống máy tính của bạn.\n\n"
        "4. **Chia Sẻ Google Sheet với Service Account:**\n"
        "   - Mở Google Sheet mà bạn muốn ghi dữ liệu.\n"
        "   - Nhấn vào nút **Share**.\n"
        "   - Thêm địa chỉ email của Service Account (có trong tệp JSON) với quyền **Editor**.\n\n"
        "5. **Thiết Lập Bot với Service Account File:**\n"
        "   - Sử dụng lệnh `/setserviceaccount` trong bot và cung cấp đường dẫn đến tệp JSON mà bạn đã tải xuống.\n\n"
        "📌 **Lưu Ý:** Đảm bảo rằng tệp `service_account.json` được lưu trữ an toàn và không được chia sẻ công khai."
    )
    await update.message.reply_text(instructions_message, parse_mode='Markdown')

# Lệnh /help để liệt kê các lệnh
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "🛠 **Danh Sách Các Lệnh Hỗ Trợ:**\n\n"
        "/sheet - Thiết lập Sheet ID để lưu dữ liệu.\n"
        "/setserviceaccount - Thiết lập đường dẫn đến tệp Service Account JSON.\n"
        "/instructions - Xem hướng dẫn tạo và thiết lập Service Account.\n"
        "/help - Hiển thị danh sách các lệnh hỗ trợ."
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')

# Hàm phân tích tin nhắn để bóc tách số tiền và mục đích
def parse_message(text):
    # Tìm số tiền (ví dụ: 10k, 5000)
    match = re.search(r'(\d+(?:[kK])?)', text)
    if not match:
        return None, None

    # Xử lý số tiền
    amount_str = match.group(1)
    if 'k' in amount_str.lower():
        amount = int(amount_str.lower().replace('k', '')) * 1000
    else:
        amount = int(amount_str)

    # Mục đích: loại bỏ số tiền khỏi tin nhắn
    purpose = text.replace(match.group(0), '').strip()
    return amount, purpose

# Hàm lưu dữ liệu vào Google Sheets sử dụng Service Account
def save_to_google_sheet(sheet_id, service_account_file, amount, purpose, timestamp):
    try:
        # Xác thực với service account
        creds = Credentials.from_service_account_file(
            service_account_file,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        # Dữ liệu cần thêm, bao gồm cột thời gian
        values = [[str(amount), purpose, timestamp]]
        body = {'values': values}

        # Ghi dữ liệu vào sheet (cập nhật tên sheet nếu cần)
        sheet.values().append(
            spreadsheetId=sheet_id,
            range="Sheet1!A:C",  # Thay "Sheet1" bằng tên sheet thực tế nếu cần
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
    except Exception as e:
        print(f"❌ Error khi lưu vào Google Sheets: {e}")

# Xử lý tin nhắn người dùng
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    amount, purpose = parse_message(text)

    if amount is None or not purpose:
        await update.message.reply_text(
            "❌ Không thể nhận diện số tiền và mục đích.\n"
            "Hãy thử lại với định dạng như '10k ăn sáng' hoặc 'ăn sáng 10k'."
        )
        return

    # Lấy thời gian hiện tại
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    await update.message.reply_text(f"Số tiền: {amount} VND\nMục đích: {purpose}\nThời gian: {current_time}")

    # Kiểm tra thông tin người dùng
    chat_id = update.effective_chat.id
    if chat_id not in user_data:
        await update.message.reply_text(
            "⚠️ Bạn cần thiết lập Sheet ID và Service Account trước khi lưu dữ liệu.\n"
            "Sử dụng lệnh /sheet và /setserviceaccount."
        )
        return
    if 'sheet_id' not in user_data[chat_id] or 'service_account_file' not in user_data[chat_id]:
        await update.message.reply_text(
            "⚠️ Bạn cần thiết lập Sheet ID và Service Account trước khi lưu dữ liệu.\n"
            "Sử dụng lệnh /sheet và /setserviceaccount."
        )
        return

    # Lưu vào Google Sheets
    sheet_id = user_data[chat_id]['sheet_id']
    service_account_file = user_data[chat_id]['service_account_file']
    save_to_google_sheet(sheet_id, service_account_file, amount, purpose, current_time)

    await update.message.reply_text("✅ Dữ liệu đã được lưu vào Google Sheets.")

# Hàm để thiết lập các lệnh cho bot
async def set_commands(application):
    commands = [
        BotCommand("sheet", "Thiết lập Sheet ID để lưu dữ liệu."),
        BotCommand("setserviceaccount", "Thiết lập đường dẫn đến tệp Service Account JSON."),
        BotCommand("instructions", "Xem hướng dẫn tạo và thiết lập Service Account."),
        BotCommand("help", "Hiển thị danh sách các lệnh hỗ trợ."),
    ]
    await application.bot.set_my_commands(commands)

# Hàm khởi tạo và chạy bot
def main():
    # Khởi tạo Application với hàm on_startup
    application = ApplicationBuilder().token(TOKEN).build()

    # Đăng ký các lệnh
    application.add_handler(CommandHandler("sheet", set_sheet))
    application.add_handler(CommandHandler("setserviceaccount", set_service_account))
    application.add_handler(CommandHandler("instructions", instructions))
    application.add_handler(CommandHandler("help", help_command))  # Thêm lệnh /help

    # Đăng ký xử lý tin nhắn
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Đăng ký hàm set_commands để thiết lập các lệnh khi bot khởi động
    async def on_startup(application):
        await set_commands(application)

    application.on_startup = on_startup

    # Chạy bot với polling (blocking call)
    application.run_polling()

if __name__ == '__main__':
    main()
