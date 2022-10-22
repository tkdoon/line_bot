import datetime
from dateutil import relativedelta
import pytz


def calculate_time(dates_list, times_list, messages):
    now = datetime.datetime.now()
    second_until_the_time = []
    datetime_data = []
    message_list = []
    DISPLAY_TIMEZONE = 'Asia/Tokyo'
    tz = pytz.timezone(DISPLAY_TIMEZONE)
    for index, dates in enumerate(dates_list):
        for date in dates:
            for time in times_list[index]:
                date_plus_time = date+time
                date_plus_time_of_this_year = str(
                    datetime.datetime.now().year)+date_plus_time
                datetime_date_plus_time = datetime.datetime.strptime(
                    date_plus_time_of_this_year, '%Y%m/%d%H:%M')
                if datetime_date_plus_time < now:
                    datetime_date_plus_time += relativedelta.relativedelta(
                        years=1)
                aware_datetime_date_plus_time = tz.localize(
                    datetime_date_plus_time)
                datetime_data.append(aware_datetime_date_plus_time)
                time_until_remind_time = datetime_date_plus_time-now
                second_until_the_time.append(
                    time_until_remind_time.total_seconds())
                message_list.append(messages[index])
    return second_until_the_time, datetime_data, message_list
