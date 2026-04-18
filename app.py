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
                text = msg["message"]["text"]
                if "http" in text:
                    send_message(sender_id, "⏳ ভিডিও ডাউনলোড হচ্ছে...")
                    download_and_send(sender_id, text)
                else:
                    send_message(sender_id, "একটা ভিডিও লিংক পাঠান!")
    return jsonify({"status": "ok"})

def send_message(recipient_id, text):
    requests.post(
        f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}",
        json={"recipient": {"id": recipient_id}, "message": {"text": text}}
    )

def download_and_send(recipient_id, url):
    try:
        ydl_opts = {"outtmpl": "/tmp/video.%(ext)s", "format": "best[filesize<25M]"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info["ext"]
        filepath = f"/tmp/video.{ext}"
        with open(filepath, "rb") as f:
            requests.post(
                f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}",
                data={"recipient": '{"id":"' + recipient_id + '"}', "message": '{"attachment":{"type":"video","payload":{}}}'},
                files={"filedata": f}
            )
        os.remove(filepath)
    except Exception as e:
        send_message(recipient_id, f"❌ ডাউনলোড হয়নি: {str(e)}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
