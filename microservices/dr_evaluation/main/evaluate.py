import pymortar
import pandas as pd
import pickle
from .utils import get_date_str
from .daily_data import get_daily_data

import os
curr_path = os.path.abspath(os.path.dirname(__file__))

def evaluate(site, date, model_name='best'):
    cli = pymortar.Client()
    date = pd.to_datetime(date).date()

    # best_model_path = './models/{}/{}'.format(site, model_name)
    best_model_path = os.path.join(curr_path + '/../models/{}/{}'.format(site, model_name))

    model_file = open(best_model_path, 'rb')
    print('model_file: ', model_file)

    best_model = pickle.load(model_file)
    actual, prediction, event_weather, baseline_weather = best_model.predict(site, date)
    weather_mean=event_weather[((event_weather.index.hour>=14) & (event_weather.index.hour<=18))].mean()
    daily_data = get_daily_data(site, actual, prediction)
    return {
        'site': site,
        'date': date,
        'cost': {
            'actual': daily_data['actual_cost'],
            'baseline': daily_data['baseline_cost']
        },
        'OAT_mean': {
            'event': weather_mean['weather'],
            'baseline': baseline_weather
        },
        'baseline-type': best_model.name,
        'baseline-rmse': best_model.rmse,
        'actual': actual.values,
        'baseline': prediction.values
    }

def to_indexed_series(array, date):
    index = pd.date_range(date, periods=96, freq='15min')
    result = pd.Series(array, index=index)
    return result
