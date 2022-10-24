import pytz
import os
import base64
import hashlib
import hmac
import datetime
from flask import abort, jsonify
from google.cloud import firestore
import calculate_time
import publish_message

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
# /set
# 10/19,10/20
# 19:00,20:00
# message
#
# 10/29
# 20:00
# message
# ;


def check_format(text):
    try:
        text = text.splitlines()
        queues = int((len(text))/4)
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
                new_dates.append(date)
            for time in times:
                new_times.append(time)
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

    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue
        db = firestore.Client()

        text = event.message.text
        user_id = event.source.user_id if event.source.type == "user" else event.source.group_id if event.source.type == "group" else "unknown_id"
        only_num_txt = text.replace(",", "")
        if text.startswith("/set"):  # テキストが/setから始まったら処理を実行
            checked = check_format(text)
            if not checked:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="フォーマットが間違っています")
                )
            else:
                calculated_time = calculate_time.calculate_time(
                    checked[0], checked[1], checked[2])
                second_until_the_times = calculated_time[0]
                try:
                    for index, second_until_the_time in enumerate(second_until_the_times):
                        message_id = db.collection(
                            'line_reminder').document().id
                        doc_ref = db.collection(
                            'line_reminder').document(f'{message_id}')
                        # firestoreにデータを送る
                        doc_ref.set({"set_date": datetime.datetime.now(
                        ), "remind_date": calculated_time[1][index], "second_until_the_time": int(second_until_the_time), "message": calculated_time[2][index], "raw_text": text, "remind": True, "user_id": user_id})
                        # トピックをパブリッシュする
                        publish_message.publish_message(
                            str(int(second_until_the_time)), message_id)
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="リマインドをセットしました")
                    )
                except Exception as e:
                    print(e)
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"リマインドのセットに失敗しました{e}")
                    )
        elif text.startswith("/cancel"):
            try:
                DISPLAY_TIMEZONE = 'Asia/Tokyo'
                tz = pytz.timezone(DISPLAY_TIMEZONE)
                db.collection("user_id").document(user_id).delete()
                user_schedules = db.collection(
                    'line_reminder').where("user_id", "==", user_id).stream()
                schedule_dict = {"index": {}, "set_time": {}}
                text_message = ""
                for index, schedule_info in enumerate(user_schedules):
                    remind_date = tz.localize(
                        datetime.datetime.strptime(schedule_info.to_dict(
                        )["remind_date"].strftime("%Y-%m-%d %H:%M"), "%Y-%m-%d %H:%M")+datetime.timedelta(hours=9))
                    message = schedule_info.to_dict()["message"]
                    schedule_dict["index"][f"{index}"] = {
                        "scheduled_date": f"{remind_date}", "message": message, "message_id": f"{schedule_info.id}"}
                    schedule_dict["set_time"] = datetime.datetime.now(tz)
                    text_message += f"\n{index} {remind_date}"
                usr_ref = db.collection("user_id").document(user_id)
                usr_ref.set(schedule_dict)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="取り消す番号を選んでください" +
                                    text_message+"\n複数取り消す場合は,で区切ってください")
                )
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"キャンセルエラー{e}")
                )
        elif only_num_txt.isdigit():
            info = db.collection("user_id").document(user_id).get().to_dict()
            DISPLAY_TIMEZONE = 'Asia/Tokyo'
            tz = pytz.timezone(DISPLAY_TIMEZONE)
            set_time = tz.localize(
                datetime.datetime.strptime(info["set_time"].strftime("%Y-%m-%d %H:%M"), "%Y-%m-%d %H:%M")+datetime.timedelta(hours=9))
            if set_time+datetime.timedelta(minutes=5) > datetime.datetime.now(tz):
                nums = text.split(",")
                for num in nums:
                    message_id = info["index"][num]["message_id"]
                    db.collection("line_reminder").document(
                        message_id).update({"remind": False})
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="キャンセル完了")
                )
            else:
                pass
        else:
            pass
    return jsonify({"message": "ok"})


# デバッグ用
# checked = check_format("//set//\n10/23\n17:53\nmessage\n;")
# calculated_time = calculate_time.calculate_time(
#     checked[0], checked[1], checked[2])
# print(calculated_time[0])
# second_until_the_times = calculated_time[0]
# for index, second_until_the_time in enumerate(second_until_the_times):
#     print(int(second_until_the_time))

# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './data-potential-365808-45ad793328a9.json'
# db = firestore.Client()
# text = "0"
# user_id = "U331cb15f936ed8361c9e05dab50f2820"

# only_num_txt = text.replace(",", "")
# if text.startswith("/cancel"):
#     DISPLAY_TIMEZONE = 'Asia/Tokyo'
#     tz = pytz.timezone(DISPLAY_TIMEZONE)
#     db.collection("user_id").document(user_id).delete()
#     user_schedules = db.collection(
#         'line_reminder').where("user_id", "==", user_id).stream()
#     schedule_dict = {"index": {}, "set_time": {}}
#     text_message = ""
#     for index, schedule_info in enumerate(user_schedules):
#         remind_date = tz.localize(
#             datetime.datetime.strptime(schedule_info.to_dict(
#             )["remind_date"].strftime("%Y-%m-%d %H:%M"), "%Y-%m-%d %H:%M")+datetime.timedelta(hours=9))

#         message = schedule_info.to_dict()["message"]
    # schedule_dict["index"][f"{index}"] = {
    #     "scheduled_date": f"{remind_date}", "message": message, "message_id": f"{schedule_info.id}"}
#         schedule_dict["set_time"] = datetime.datetime.now(tz)
#         text_message += f"\n{index} {remind_date}"
#     usr_ref = db.collection("user_id").document(user_id)
#     usr_ref.set(schedule_dict)
#     print("取り消す番号を選んでください" +
#           text_message+"\n複数取り消す場合は,で区切ってください")


# elif only_num_txt.isdigit():
#     info = db.collection("user_id").document(user_id).get().to_dict()
#     DISPLAY_TIMEZONE = 'Asia/Tokyo'
#     tz = pytz.timezone(DISPLAY_TIMEZONE)
#     set_time = tz.localize(
#         datetime.datetime.strptime(info["set_time"].strftime("%Y-%m-%d %H:%M"), "%Y-%m-%d %H:%M")+datetime.timedelta(hours=9))
#     if set_time+datetime.timedelta(minutes=5) > datetime.datetime.now(tz):
#         nums = text.split(",")
#         for num in nums:
#             message_id = info["index"][num]["message_id"]
#             db.collection("line_reminder").document(
#                 message_id).update({"remind": False})
#     else:
#         pass
