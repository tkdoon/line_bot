import datetime


def calculate_time(dates_list, times_list):
    now = datetime.datetime.now()
    second_until_the_time = []
    for index, dates in enumerate(dates_list):
        for date in dates:
            for time in times_list[index]:
                date_plus_time = date+time
                date_plus_time_of_this_year = str(
                    datetime.datetime.now().year)+date_plus_time
                datetime_date_plus_time = datetime.datetime.strptime(
                    date_plus_time_of_this_year, '%Y%m/%d%H:%M')
                if datetime_date_plus_time < now:
                    datetime_date_plus_time += datetime.timedelta(years=1)
                time_until_remind_time = datetime_date_plus_time-now
                second_until_the_time.append(
                    time_until_remind_time.total_seconds())
    return second_until_the_time
