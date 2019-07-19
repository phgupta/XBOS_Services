import json
import pytz
import datetime
import xbos_services_getter
UTC_TZ = pytz.timezone('UTC')

def round_minutes(dt, direction, resolution):
    """ Round the minutes part of datetime.

    Parameters
    ----------
    dt          : datetime.datetime()
        Datetime object to be rounded up/down.
    direction   : str
        Round up or round down. Possible values are 'up' and 'down'.
    resolution  : int
        Resolution of rounding off. e.g. 15m, 30m, 60m etc.

    Returns
    -------
    datetime.datetime
        Rounded off datetime value

    """
    new_minute = (dt.minute // resolution + (1 if direction == 'up' else 0)) * resolution
    return dt + datetime.timedelta(minutes=new_minute - dt.minute)


with open('models/ciee-model.json') as json_file:
    model_info = json.load(json_file)

window = 15
# date_today = datetime.datetime.today()
# curr_time_rounded = round_minutes(date_today, 'down', window)
# start_time = curr_time_rounded - datetime.timedelta(minutes=model_info['num_prev_minutes'])

start_time = datetime.datetime(2018, 7, 9, 12, 0, 0)
curr_time_rounded = datetime.datetime(2019, 7, 15, 18, 0, 0)

print('start_time: ', start_time)
print('end_time: ', curr_time_rounded)

# prev_minutes to curr_time historic data
indoor_historic_stub = xbos_services_getter.get_indoor_historic_stub()
historic_states = xbos_services_getter.get_indoor_actions_historic(indoor_historic_stub,
                                                                   building='ciee',
                                                                   zone='hvac_zone_eastzone',
                                                                   start=start_time,
                                                                   end=curr_time_rounded,
                                                                   window=str(window)+'m',
                                                                   agg='MAX')
print('historic_states: ', historic_states)
