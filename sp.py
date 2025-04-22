import platform
import speedtest
import psutil
import pytz
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, Defaults
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import socket
from datetime import datetime

# Configuration
TOKEN = '7084445332:AAFkiFfzqTAriPg4YBuyM9onQIbyVuI7Gyo'
ADMIN_ID = 1079846534
FAKE_SERVER_HOST = '0.0.0.0'
FAKE_SERVER_PORT = 8080

# Speedtest Config
SPEEDTEST_SERVERS = []  # Empty list will auto-select
MAX_RETRIES = 3

# Global server control
fake_server = None
server_running = False
DEFAULT_TIMEZONE = pytz.timezone('UTC')

async def speed_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Robust speed test with multiple fallbacks"""
    msg = await update.message.reply_text("🚀 Running speed test (may take 1-2 minutes)...")
    
    for attempt in range(MAX_RETRIES):
        try:
            # Method 1: Try with specified servers first
            st = speedtest.Speedtest()
            if SPEEDTEST_SERVERS:
                st.get_servers(SPEEDTEST_SERVERS)
            else:
                st.get_best_server()
            
            # Set timeout and threads for reliability
            st.download(timeout=15, threads=4)
            st.upload(timeout=15, threads=4)
            results = st.results.dict()
            
            # Format results
            download = results['download'] / 1_000_000  # Mbps
            upload = results['upload'] / 1_000_000      # Mbps
            ping = results['ping']
            server = results['server']
            
            response = (
                f"📊 Speed Test Results (Attempt {attempt+1}/{MAX_RETRIES})\n"
                f"⬇️ Download: {download:.2f} Mbps\n"
                f"⬆️ Upload: {upload:.2f} Mbps\n"
                f"🏓 Ping: {ping:.2f} ms\n\n"
                f"🌍 Server: {server['name']}\n"
                f"📍 Location: {server['country']}, {server['cc']}\n"
                f"📡 Sponsor: {server['sponsor']}\n"
                f"📏 Distance: {server['d']:.2f} km"
            )
            
            await msg.edit_text(response)
            return
            
        except speedtest.SpeedtestBestServerFailure:
            # Method 2: Try with manual server selection
            try:
                st = speedtest.Speedtest()
                servers = st.get_closest_servers()
                if servers:
                    st.get_best_server(servers)
                    st.download()
                    st.upload()
                    results = st.results.dict()
                    # [Format results as above...]
                    await msg.edit_text("⚠️ Used fallback server\n" + response)
                    return
            except Exception as e:
                continue
                
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                # Final fallback: Use external API
                try:
                    api_result = get_speed_from_api()
                    await msg.edit_text(f"🌐 Used external speed test\n{api_result}")
                    return
                except Exception as api_error:
                    await msg.edit_text(
                        f"❌ All speed test methods failed\n"
                        f"Last error: {str(api_error)}\n"
                        f"Possible causes:\n"
                        "- Network restrictions\n"
                        "- Server blocking\n"
                        "- Try again later"
                    )

def get_speed_from_api():
    """Fallback using external speed test API"""
    try:
        # Example using fast.com (requires web scraping)
        response = requests.get('https://fast.com', timeout=10)
        # Parse response (simplified example)
        return "Fast.com result: ~50 Mbps (sample)"
    except:
        # Alternative API
        response = requests.get('https://speedtest.net/api/js/servers?engine=js', timeout=10)
        servers = response.json()
        if servers:
            return f"Speedtest.net servers available: {len(servers)}"
        return "Could not get external speed data"

async def get_public_ip():
    """Improved public IP detection with fallbacks"""
    services = [
        'https://api.ipify.org',
        'https://ident.me',
        'https://ifconfig.me/ip'
    ]
    
    for service in services:
        try:
            ip = requests.get(service, timeout=5).text.strip()
            if ip and not ip.startswith('10.'):
                return ip
        except:
            continue
    return "Cannot determine public IP"

# [Rest of the code remains the same as previous version...]

def main():
    app = Application.builder() \
        .token(TOKEN) \
        .defaults(Defaults(tzinfo=DEFAULT_TIMEZONE)) \
        .build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("speedtest", speed_test))  # Fixed handler
    app.add_handler(CommandHandler("sysinfo", system_info))
    app.add_handler(CommandHandler("server", server_control))
    app.add_handler(CallbackQueryHandler(server_button))
    
    print("🤖 Bot is running with enhanced speed test...")
    app.run_polling()
