from twilio.rest import Client
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AlertManager:
    def __init__(self, account_sid, auth_token, from_number, to_number, voice_message, sms_message, testing_mode=False):
        self.client = Client(account_sid, auth_token) if not testing_mode else None
        self.from_number = from_number
        self.to_number = to_number
        self.voice_message = voice_message
        self.sms_message = sms_message
        self.testing_mode = testing_mode
        self.alert_count = 0

    def send_sms(self):
        self.alert_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.testing_mode:
            logger.warning(f"[ALERT #{self.alert_count}] {timestamp} - SMS ALERT (Testing Mode)")
            logger.warning(f"  TO: {self.to_number}")
            logger.warning(f"  Message: {self.sms_message}")
            print(f"\n{'='*60}")
            print(f"🚨 SMS ALERT SENT (Testing Mode) - Alert #{self.alert_count}")
            print(f"{'='*60}")
            print(f"Timestamp: {timestamp}")
            print(f"To: {self.to_number}")
            print(f"Message: {self.sms_message}")
            print(f"{'='*60}\n")
            return
        
        try:
            message = self.client.messages.create(
                body=self.sms_message,
                from_=self.from_number,
                to=self.to_number
            )
            logger.info(f"SMS sent: {message.sid}")
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")

    def make_call(self):
        self.alert_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.testing_mode:
            logger.warning(f"[ALERT #{self.alert_count}] {timestamp} - VOICE CALL ALERT (Testing Mode)")
            logger.warning(f"  TO: {self.to_number}")
            logger.warning(f"  Message: {self.voice_message}")
            print(f"\n{'='*60}")
            print(f"🚨 VOICE CALL ALERT (Testing Mode) - Alert #{self.alert_count}")
            print(f"{'='*60}")
            print(f"Timestamp: {timestamp}")
            print(f"To: {self.to_number}")
            print(f"Voice Message: {self.voice_message}")
            print(f"{'='*60}\n")
            return
        
        try:
            call = self.client.calls.create(
                twiml=f'<Response><Say>{self.voice_message}</Say></Response>',
                from_=self.from_number,
                to=self.to_number
            )
            logger.info(f"Call initiated: {call.sid}")
        except Exception as e:
            logger.error(f"Failed to make call: {e}")

    def send_alert(self, event_type="unknown"):
        """Send both SMS and call alert"""
        logger.critical(f"SECURITY ALERT: {event_type.upper()}")
        self.send_sms()
        self.make_call()
