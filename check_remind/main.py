from email import message
import os
import base64
import hashlib
import hmac
import logging
import datetime
from flask import abort, jsonify

from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage
)


# フォーマットは
# //set//
# 10/19,10/20
# 19:00,20:00
# message
#
# 10/29
# 20:00
# message
# ;

def check_date(date):
    try:
        new_date = datetime.datetime.strptime(date, '%m/%d')
        return new_date
    except ValueError:
        return False


def check_time(time):
    try:
        new_time = datetime.datetime.strptime(time, '%H%M')
        return new_time
    except ValueError:
        return False


def check_format(text):
    try:
        text = text.splitlines()
        queues = text.length/4
        dates_list = []
        times_list = []
        messages = []
        for i in range(queues):
            dates = text[4*i+1].split(',')
            times = text[4*i+2].split(',')
            message = text[4*i+3]
            new_dates = []
            new_times = []
            for date in dates:
                if not check_date(date):
                    return False
                else:
                    new_dates.append(check_date(date))
            for time in times:
                if not check_time(time):
                    return False
                else:
                    new_times.append(check_time(time))
            dates_list.append(new_dates)
            times_list.append(new_times)
            messages.append(message)

        return dates_list, times_list, messages

    except Exception as e:
        print(e)
        return False


def main(request):
    channel_secret = os.environ.get('LINE_CHANNEL_SECRET')
    channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')

    line_bot_api = LineBotApi(channel_access_token)
    parser = WebhookParser(channel_secret)

    body = request.get_data(as_text=True)
    hash = hmac.new(channel_secret.encode('utf-8'),
                    body.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode()

    if signature != request.headers['X_LINE_SIGNATURE']:
        return abort(405)

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        return abort(405)
    text = "no_message"
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

        text = event.message.text
        if text.startswith("//set//"):  # テキストが//set//だったら処理を実行
            if not check_format(text):
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="フォーマットが間違っています")
                )
            else:

        else:
            pass
    return jsonify({"message": "ok"})
