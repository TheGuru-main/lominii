"""OTP Service – generate, send, verify via Africa's Talking (Platform Layer)"""
import os
import random
import africastalking

# Initialize Africa's Talking
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")   # "sandbox" for free tier
AT_API_KEY = os.getenv("AT_API_KEY", "your-sandbox-key")

africastalking.initialize(AT_USERNAME, AT_API_KEY)
sms = africastalking.SMS

def generate_otp() -> str:
    """Generate a 6‑digit OTP."""
    return str(random.randint(100000, 999999))

async def send_otp(phone: str, otp: str) -> bool:
    """Send OTP via Africa's Talking SMS. Returns True on success."""
    try:
        message = f"Your LOMINII verification code is: {otp}"
        # Africa's Talking requires international format (+234…)
        recipients = [phone] if phone.startswith("+") else ["+" + phone]
        response = sms.send(message, recipients)
        return response["SMSMessageData"]["Recipients"][0]["status"] == "Success"
    except Exception:
        return False