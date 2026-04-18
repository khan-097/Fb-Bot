import os
import requests
import yt_dlp
from flask import Flask, request, jsonify

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Invalid token", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    for entry in data.get("entry", []):
        for msg in entry.get("messaging", []):
            sender_id = msg["sender"]["id"]
            if "message" in msg and "text" in msg["message"]:
                text = msg["message"]["text"].strip()
                if "http" in text:
                    send_message(sender_id, "⏳ ভিডিও ডাউনলোড হচ্ছে, একটু অপেক্ষা করুন...")
                    download_and_send(sender_id, text)
                else:
                    send_message(sender_id, "🎬 একটা ভিডিও লিংক পাঠান!\n\nSupported:\n▶️ YouTube\n📘 Facebook\n📸 Instagram\n🎵 TikTok")
    return jsonify({"status": "ok"})

def send_message(recipient_id, text):
    requests.post(
        f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}",
        json={"recipient": {"id": recipient_id}, "message": {"text": text}}
    )

def download_and_send(recipient_id, url):
    try:
        ydl_opts = {
            "outtmpl": "/tmp/video.%(ext)s",
            "format": "best[ext=mp4][filesize<25M]/best[filesize<25M]/best",
            "max_filesize": 24000000,
            "noplaylist": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"]
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36"
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get("ext", "mp4")
            title = info.get("title", "ভিডিও")

        filepath = f"/tmp/video.{ext}"

        if not os.path.exists(filepath):
            send_message(recipient_id, "❌ ফাইল তৈরি হয়নি, আবার চেষ্টা করুন।")
            return

        filesize = os.path.getsize(filepath)
        if filesize > 25000000:
            os.remove(filepath)
            send_message(recipient_id, "❌ ভিডিওটা অনেক বড় (25MB এর বেশি)। ছোট ভিডিও পাঠান।")
            return

        send_message(recipient_id, f"✅ ডাউনলোড হয়েছে: {title}\n📤 পাঠানো হচ্ছে...")

        with open(filepath, "rb") as f:
            response = requests.post(
                f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}",
                data={
                    "recipient": '{"id":"' + recipient_id + '"}',
                    "message": '{"attachment":{"type":"video","payload":{}}}'
                },
                files={"filedata": (f"video.{ext}", f, "video/mp4")}
            )

        os.remove(filepath)

        if response.status_code != 200:
            send_message(recipient_id, "❌ ভিডিও পাঠাতে সমস্যা হয়েছে।")

    except Exception as e:
        error = str(e)
        if "Sign in" in error or "bot" in error:
            send_message(recipient_id, "❌ YouTube এই ভিডিওটা block করেছে। অন্য লিংক চেষ্টা করুন।")
        elif "too large" in error or "filesize" in error:
            send_message(recipient_id, "❌ ভিডিওটা অনেক বড়। ছোট ভিডিও পাঠান।")
        else:
            send_message(recipient_id, f"❌ ডাউনলোড হয়নি। লিংকটা সঠিক কিনা দেখুন।")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
