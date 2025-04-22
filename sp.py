import platform
import speedtest
import psutil
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, Defaults
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import socket
from datetime import datetime

# Configuration
TOKEN = '7084445332:AAFkiFfzqTAriPg4YBuyM9onQIbyVuI7Gyo'
ADMIN_ID = 1079846534  # Replace with your numeric Telegram ID
FAKE_SERVER_HOST = '0.0.0.0'
FAKE_SERVER_PORT = 8080

# Global server control
fake_server = None
server_running = False

# Timezone setup
DEFAULT_TIMEZONE = pytz.timezone('UTC')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown_v2(
        fr'Hi {update.effective_user.mention_markdown_v2()}\! '
        r'I\'m your system monitoring bot\. '
        r'Use /help for commands\.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
📚 Available Commands:
/start - Start the bot
/help - Show this message
/speedtest - Test internet speed
/sysinfo - Show system information
/server - Control web server (admin)
"""
    await update.message.reply_text(help_text)

async def speed_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fixed speedtest command implementation"""
    msg = await update.message.reply_text("🚀 Running speed test...")
    
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        
        download = st.download() / 1_000_000  # Convert to Mbps
        upload = st.upload() / 1_000_000      # Convert to Mbps
        ping = st.results.ping
        
        server = st.get_best_server()
        result = (
            f"📊 Speed Test Results:\n"
            f"⬇️ Download: {download:.2f} Mbps\n"
            f"⬆️ Upload: {upload:.2f} Mbps\n"
            f"🏓 Ping: {ping:.2f} ms\n\n"
            f"🌍 Server: {server['name']}\n"
            f"📍 Location: {server['country']}\n"
            f"📡 Distance: {server['d']:.2f} km"
        )
        
        await msg.edit_text(result)
    except Exception as e:
        await msg.edit_text(f"❌ Speed test failed: {str(e)}")

async def get_system_info():
    """Safe system information gathering"""
    info = {}
    
    try:
        sys = platform.uname()
        info.update({
            'system': f"{sys.system} {sys.release}",
            'machine': sys.machine,
            'processor': sys.processor
        })
    except Exception:
        info.update({
            'system': "N/A",
            'machine': "N/A",
            'processor': "N/A"
        })

    try:
        info['cpu'] = f"{psutil.cpu_percent()}% ({psutil.cpu_count()} cores)"
    except Exception:
        info['cpu'] = "N/A"

    try:
        mem = psutil.virtual_memory()
        info['memory'] = f"{mem.used/1e9:.1f}GB/{mem.total/1e9:.1f}GB ({mem.percent}%)"
    except Exception:
        info['memory'] = "N/A"

    try:
        disk = psutil.disk_usage('/')
        info['storage'] = f"{disk.used/1e9:.1f}GB/{disk.total/1e9:.1f}GB ({disk.percent}%)"
    except Exception:
        info['storage'] = "N/A"

    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        info['network'] = f"Local IP: {local_ip}\nPublic IP: {get_public_ip()}"
    except Exception:
        info['network'] = "N/A"

    try:
        uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
        info['uptime'] = str(uptime).split('.')[0]
    except Exception:
        info['uptime'] = "N/A"

    return info

def get_public_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "Not available"

async def system_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    info = await get_system_info()
    
    response = (
        f"🖥️ System Information\n\n"
        f"💻 OS: {info['system']}\n"
        f"🖥️ Machine: {info['machine']}\n"
        f"⚙️ Processor: {info['processor']}\n\n"
        f"🧠 CPU: {info['cpu']}\n"
        f"📊 Memory: {info['memory']}\n"
        f"💾 Storage: {info['storage']}\n\n"
        f"🌐 Network:\n{info['network']}\n\n"
        f"⏱️ Uptime: {info['uptime']}"
    )
    
    await update.message.reply_text(response)

class SimpleHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"""
            <html><body>
                <h1>Test Server Running</h1>
                <p>This is a test web server</p>
            </body></html>
        """)

def run_server():
    global fake_server, server_running
    try:
        fake_server = HTTPServer((FAKE_SERVER_HOST, FAKE_SERVER_PORT), SimpleHTTPHandler)
        server_running = True
        fake_server.serve_forever()
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_running = False

async def server_control(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Admin only command")
        return
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    buttons = [
        [InlineKeyboardButton("▶️ Start Server", callback_data='start_server')],
        [InlineKeyboardButton("⏹️ Stop Server", callback_data='stop_server')],
        [InlineKeyboardButton("🔍 Server Status", callback_data='server_status')]
    ]
    
    message = (
        f"🖥️ Server Controls\n\n"
        f"🌐 Access URL:\n"
        f"Local: http://{local_ip}:{FAKE_SERVER_PORT}\n"
        f"Public: http://{get_public_ip()}:{FAKE_SERVER_PORT}"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def server_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    global server_running, fake_server
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    if query.data == 'start_server' and not server_running:
        threading.Thread(target=run_server, daemon=True).start()
        time.sleep(1)
        await query.edit_message_text(
            f"✅ Server started\n\n"
            f"🔗 Local URL: http://{local_ip}:{FAKE_SERVER_PORT}\n"
            f"🌍 Public URL: http://{get_public_ip()}:{FAKE_SERVER_PORT}"
        )
    elif query.data == 'stop_server' and server_running:
        fake_server.shutdown()
        fake_server.server_close()
        await query.edit_message_text("✅ Server stopped")
    elif query.data == 'server_status':
        status = "🟢 Running" if server_running else "🔴 Stopped"
        urls = ""
        if server_running:
            urls = (
                f"\n\n🔗 Local URL: http://{local_ip}:{FAKE_SERVER_PORT}\n"
                f"🌍 Public URL: http://{get_public_ip()}:{FAKE_SERVER_PORT}"
            )
        await query.edit_message_text(f"Server Status: {status}{urls}")

def main():
    app = Application.builder() \
        .token(TOKEN) \
        .defaults(Defaults(tzinfo=DEFAULT_TIMEZONE)) \
        .build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("speedtest", speed_test))  # Fixed handler
    app.add_handler(CommandHandler("sysinfo", system_info))
    app.add_handler(CommandHandler("server", server_control))
    app.add_handler(CallbackQueryHandler(server_button))
    
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()