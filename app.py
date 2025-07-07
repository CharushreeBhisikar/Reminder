import threading
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
import schedule
import time
from twilio.rest import Client
import dateparser
import re
import os

# Timezone (for Unix systems)
os.environ['TZ'] = 'Asia/Kolkata'
try:
    time.tzset()
except:
    pass

app = Flask(__name__)
reminders = []

# Twilio credentials
account_sid = 'AC0f012f92bc8c43d5b420810731e82a98' # Replace with your Twilio SID
auth_token = '1fdab63904962f08b1eda2a5f16e50f7'
twilio_client = Client(account_sid, auth_token)
from_number = 'whatsapp:+14155238886'

def extract_time_text(message):
    patterns = [
        r"(tomorrow\s+at\s+\d{1,2}(:\d{2})?\s*(am|pm))",
        r"(today\s+at\s+\d{1,2}(:\d{2})?\s*(am|pm))",
        r"(\d{1,2}(:\d{2})?\s*(am|pm))"
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(0)
    return None

def generate_confirmation(task, time_obj):
    return f"Noted! I’ll remind you to '{task}' on {time_obj.strftime('%A, %d %B %Y at %I:%M %p')}."

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip()
    sender_number = request.values.get("From", "")
    resp = MessagingResponse()
    msg = resp.message()

    time_text = extract_time_text(incoming_msg)
    parsed_time = None
    if time_text:
        parsed_time = dateparser.parse(time_text, settings={
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.now(),
            'TIMEZONE': 'Asia/Kolkata',
            'RETURN_AS_TIMEZONE_AWARE': False
        })

    if parsed_time:
        parsed_time = parsed_time.replace(second=0, microsecond=0)
        task_text = incoming_msg.replace(time_text, "").strip().rstrip(".,;:") or "do the task"
        for r in reminders:
            if r[0] == parsed_time and r[2] == sender_number:
                msg.body("You already have a reminder at that time.")
                return str(resp)

        reminders.append((parsed_time, task_text, sender_number))
        msg.body("✅ " + generate_confirmation(task_text, parsed_time))
    else:
        msg.body("⚠️ I couldn’t understand the time. Try: 'Remind me to drink water at 3 PM today'")

    return str(resp)

# 📌 Reminder Checker
def check_reminders():
    now = datetime.now().replace(second=0, microsecond=0)
    for rem_time, message, number in list(reminders):
        if rem_time == now:
            try:
                twilio_client.messages.create(
                    body=f"🔔 Reminder: {message}",
                    from_=from_number,
                    to='whatsapp:+919579793742'
                )
                print(f"✅ Reminder sent to {number}: {message}")
                reminders.remove((rem_time, message, number))
            except Exception as e:
                print(f"❌ Error sending reminder: {e}")

# 🧵 Background scheduler thread
def run_scheduler():
    schedule.every(15).seconds.do(check_reminders)
    while True:
        schedule.run_pending()
        time.sleep(1)

# 🚀 Start Flask + Scheduler
if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    print("Flask app running with reminder scheduler...")
    app.run(port=5000)
