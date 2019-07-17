import pymortar
import pandas as pd
import os
import numpy as np

from .utils import get_closest_station
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))+'/'
cli = pymortar.Client()

# def adjust(df, site):
#     site_map = pd.read_csv(os.path.join(PROJECT_ROOT, 'site_meters_map.csv'), index_col='site')
#     multiplier=site_map.loc[site,'eagle_multiplier']
#     df_adjusted=df*multiplier
#     return df_adjusted, multiplier

def adjust(df):
    for meter in df.columns.values:
        multiplier_map=pd.read_csv(os.path.join(PROJECT_ROOT, 'site_meters_map.csv'),index_col='Electric_Meter')
        #multiplier_map=site_map.set_index('Electric_Meter')
        multiplier=multiplier_map.loc[meter,'eagle_multiplier']
        df[[meter]]=df[[meter]]*multiplier
    if len(df.columns)>1:
        df=pd.DataFrame(df.sum(axis=1))
        df.columns=['combined meters']
    return df

def get_weather(site, start, end, agg, window, cli):
    weather_query = """SELECT ?t
    WHERE {
            ?t rdf:type/rdfs:subClassOf* brick:Weather_Temperature_Sensor
        };"""
    query_agg = eval('pymortar.' + str.upper(agg))
    request = pymortar.FetchRequest(
        sites=[site],
        views = [
            pymortar.View(name='weather', definition=weather_query)
        ],
        time = pymortar.TimeParams(start=start, end=end),
        dataFrames=[
            pymortar.DataFrame(
            name='weather',
            aggregation=query_agg,
            window=window,
            timeseries=[
                pymortar.Timeseries(
                    view='weather',
                    dataVars=['?t'])
            ])
        ]
    )
    result = cli.fetch(request)
    return result['weather']


def get_power(site, start, end, agg, window, cli):

    eagle_power_query = """SELECT ?meter WHERE {
            ?meter rdf:type brick:Building_Electric_Meter
        };"""

    gb_power_query = """SELECT ?meter WHERE {
            ?meter rdf:type brick:Green_Button_Meter
        };"""
    query_agg = eval('pymortar.' + str.upper(agg))
    request_gb = pymortar.FetchRequest(
        sites=[site],
        views = [
            pymortar.View(name='power', definition=gb_power_query)
        ],
        time = pymortar.TimeParams(start=start, end=end),
        dataFrames=[
            pymortar.DataFrame(
            name='power',
            aggregation=query_agg,
            window=window,
            timeseries=[
                pymortar.Timeseries(
                    view='power',
                    dataVars=['?meter'])
            ])
        ]
    )
    request_eagle = pymortar.FetchRequest(
        sites=[site],
        views = [
            pymortar.View(name='power', definition=eagle_power_query)
        ],
        time = pymortar.TimeParams(start=start, end=end),
        dataFrames=[
            pymortar.DataFrame(
            name='power',
            aggregation=query_agg,
            window=window,
            timeseries=[
                pymortar.Timeseries(
                    view='power',
                    dataVars=['?meter'])
            ])
        ]
    )
    result_gb = cli.fetch(request_gb)
    result_eagle = cli.fetch(request_eagle)
    try:
        power_gb=result_gb['power']*4000 #adjusts to from energy to power (15 min period), and from kw to w
        power_eagle=adjust(result_eagle['power'])
        power_eagle.columns=[power_gb.columns[0]]
        power=power_gb.fillna(value=power_eagle) # power uses available gb data, fills NA with eagle data
    except:
        if np.size(result_gb['power'])>1:
            power=result_gb['power']*4000
        elif np.size(result_eagle['power'])>1:
            power=adjust(result_eagle['power'])
        else:
            print("no data")


    return power

def get_df(site, start, end, agg='MEAN', interval='15min'):

    # Get weather
    weather = get_weather(site, start, end, agg=agg, window=interval, cli=cli)
    if weather.index.tz is None:
        weather.index = weather.index.tz_localize('UTC')
    weather.index = weather.index.tz_convert('US/Pacific')

    closest_station = get_closest_station(site)
    if closest_station is not None:
        weather = pd.DataFrame(weather[closest_station])
    else:
        weather = pd.DataFrame(weather.mean(axis=1))

    # Get power
    power = get_power(site, start, end, agg=agg, window=interval, cli=cli)

    if power.index.tz is None:
        power.index = power.index.tz_localize('UTC')
    power.index = power.index.tz_convert('US/Pacific')

    # Merge
    power_sum = pd.DataFrame(power.sum(axis=1))
    data = power_sum.merge(weather, left_index=True, right_index=True)
    data.columns = ['power', 'weather']

    return data
