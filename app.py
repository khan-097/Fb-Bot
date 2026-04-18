import os
import requests
import yt_dlp
from flask import Flask, request, jsonify

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
processed_ids = set()

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
            mid = msg.get("message", {}).get("mid", "")
            if mid in processed_ids:
                continue
            processed_ids.add(mid)
            sender_id = msg["sender"]["id"]
            if "message" in msg and "text" in msg["message"]:
                text = msg["message"]["text"].strip()
                if "http" in text:
                    send_message(sender_id, "অপেক্ষা করুন, ভিডিও ডাউনলোড হচ্ছে... ⏰")
                    download_and_send(sender_id, text)
                else:
                    send_message(sender_id, "🎬 একটা ভিডিও লিংক পাঠান!\n\n▶️ YouTube\n📘 Facebook\n📸 Instagram\n🎵 TikTok")
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
            "format": "best[ext=mp4][filesize<24M]/best[filesize<24M]/best",
            "noplaylist": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "web"]
                }
            },
            "http_headers": {
                "User-Agent": "com.google.android.youtube/17.36.4 (Linux; U; Android 12) gzip"
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get("ext", "mp4")

        filepath = f"/tmp/video.{ext}"

        if not os.path.exists(filepath):
            send_message(recipient_id, "❌ ফাইল তৈরি হয়নি।")
            return

        if os.path.getsize(filepath) > 25000000:
            os.remove(filepath)
            send_message(recipient_id, "❌ ভিডিও অনেক বড় (25MB+)।")
            return

        with open(filepath, "rb") as f:
            requests.post(
                f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}",
                data={
                    "recipient": '{"id":"' + recipient_id + '"}',
                    "message": '{"attachment":{"type":"video","payload":{}}}'
                },
                files={"filedata": (f"video.{ext}", f, "video/mp4")}
            )

        os.remove(filepath)
        send_message(recipient_id, "⬆️ DOWNLOADED BY KHAN-J7 ⬆️")

    except Exception as e:
        error = str(e)
        if "Sign in" in error or "bot" in error:
            send_message(recipient_id, "❌ YouTube block করেছে। অন্য লিংক চেষ্টা করুন।")
        else:
            send_message(recipient_id, "❌ ডাউনলোড হয়নি।")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
