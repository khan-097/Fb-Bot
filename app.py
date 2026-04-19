import os
import requests
import yt_dlp
from flask import Flask, request, jsonify

app = Flask(_name_)

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

def get_download_url_cobalt(url):
    try:
        response = requests.post(
            "https://api.cobalt.tools/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json={
                "url": url,
                "videoQuality": "720",
                "filenameStyle": "basic"
            },
            timeout=30
        )
        data = response.json()
        if data.get("status") in ["stream", "redirect", "tunnel"]:
            return data.get("url")
        elif data.get("status") == "picker":
            return data["picker"][0]["url"]
        return None
    except:
        return None

def download_and_send(recipient_id, url):
    try:
        # প্রথমে cobalt দিয়ে চেষ্টা (YouTube এর জন্য)
        download_url = None
        is_youtube = "youtube.com" in url or "youtu.be" in url

        if is_youtube:
            download_url = get_download_url_cobalt(url)

        if download_url:
            # cobalt থেকে download
            response = requests.get(download_url, timeout=60, stream=True)
            filepath = "/tmp/video.mp4"
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            # Facebook/Instagram/TikTok এর জন্য yt-dlp
            ydl_opts = {
                "outtmpl": "/tmp/video.%(ext)s",
                "format": "best[ext=mp4][filesize<24M]/best[filesize<24M]/best",
                "noplaylist": True,
                "merge_output_format": "mp4",
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                ext = info.get("ext", "mp4")

            filepath = f"/tmp/video.{ext}"
            if not os.path.exists(filepath):
                filepath = "/tmp/video.mp4"

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
                files={"filedata": ("video.mp4", f, "video/mp4")}
            )

        os.remove(filepath)
        send_message(recipient_id, "⬆️ DOWNLOADED BY KHAN-J7 ⬆️")

    except Exception as e:
        error = str(e)
        if "429" in error or "Too Many" in error:
            send_message(recipient_id, "❌ YouTube busy। ১ মিনিট পরে চেষ্টা করুন।")
        elif "filesize" in error or "large" in error:
            send_message(recipient_id, "❌ ভিডিও অনেক বড়।")
        else:
            send_message(recipient_id, "❌ ডাউনলোড হয়নি। অন্য লিংক চেষ্টা করুন।")

if _name_ == "_main_":
    app.run(host="0.0.0.0", port=5000)
