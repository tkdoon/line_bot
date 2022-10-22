from google.cloud import firestore
from linebot import (
    LineBotApi
)
from linebot.models import TextSendMessage
import secret_id

db = firestore.Client()


def get_info(message_id):
    docs = db.collection('line_reminder').document(message_id).get().to_dict()
    if docs["remind"]:
        user_id = docs["user_id"]
        message = docs["message"]
        return user_id, message
    else:
        return False


def main(message):
    LINE_CHANNEL_ACCESS_TOKEN = secret_id.access_token
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    if get_info(message):
        user_id = get_info(message)[0]

        messages = TextSendMessage(text=get_info(message)[1])
        line_bot_api.push_message(user_id, messages=messages)
    else:
        pass
    db.collection('line_reminder').document(message).delete()
    return {"message": "ok"}
