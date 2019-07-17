from electricitycostcalculator.cost_calculator.cost_calculator import CostCalculator
from electricitycostcalculator.openei_tariff.openei_tariff_analyzer import *
from electricitycostcalculator.cost_calculator.tariff_structure import *
from .utils import  get_month_window
from .get_greenbutton_id import *
import datetime as dtime
from datetime import timedelta
from .get_data import get_df
import numpy as np
import pandas as pd
import math
import os

calculator = CostCalculator()
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))+'/'

def eval_nan(x):
    if (not type(x) == str) and math.isnan(x):
        return None
    return x

def calc_price(power_vector, site, start_datetime, end_datetime):
    tarrifs = pd.read_csv(os.path.join(PROJECT_ROOT, 'tariffs.csv'), index_col='meter_id')
    meter_id = get_greenbutton_id(site)
    tariff = tarrifs.loc[meter_id]
    tariff = dict(tariff)
    tariff['distrib_level_of_interest'] = eval_nan(tariff['distrib_level_of_interest'])
    tariff['option_exclusion'] = eval_nan(tariff['option_exclusion'])
    tariff['option_mandatory'] = eval_nan(tariff['option_mandatory'])

    total_price = calc_total_price(power_vector, tariff, start_datetime, end_datetime, site)
    return total_price

def calc_total_price(power_vector, tariff_options, start_datetime, end_datetime, site, interval='15min'):
    '''
    returns the total energy cost of power consumption over the given window
    the granularity is determined from the length of the vector and the time window
    TODO: Demand charges

    power_vector: a pandas series of power consumption (kW) over the given window
    tariff_options: a dictionary of the form {
        utility_id: '14328',
        sector: 'Commercial',
        tariff_rate_of_interest: 'A-1 Small General Service',
        distrib_level_of_interest=None, #TODO: Figure out what this is
        phasewing='Single',
        tou=True
    }
    start_datetime: the datetime object representing the start time (starts )
    end_datetime: the datetime object representing the start time
    '''
    time_delta = end_datetime - start_datetime
    interval_15_min = (3600*24*time_delta.days + time_delta.seconds)/(60*15)
    if len(power_vector) == interval_15_min or interval == '15min':
        energy_vector = power_15min_to_hourly_energy(power_vector)
        energy_vector.index = pd.date_range(start=start_datetime, end=end_datetime, freq='1h')
    else:
        energy_vector = power_vector
    energy_vector = energy_vector / 1000
    if pd.isna(tariff_options['phasewing']):
        tariff_options['phasewing'] = None
    tariff = OpenEI_tariff(tariff_options['utility_id'],
                  tariff_options['sector'],
                  tariff_options['tariff_rate_of_interest'],
                  tariff_options['distrib_level_of_interest'],
                  tariff_options['phasewing'],
                  tariff_options['tou'],
                  option_exclusion=tariff_options['option_exclusion'],
                  option_mandatory=tariff_options['option_mandatory'])
    tariff.read_from_json()
    tariff_struct_from_openei_data(tariff, calculator, pdp_event_filenames='PDP_events.json')
    pd_prices, map_prices = calculator.get_electricity_price(timestep=TariffElemPeriod.HOURLY,
                                                        range_date=(start_datetime.replace(tzinfo=pytz.timezone('US/Pacific')),
                                                                    end_datetime.replace(tzinfo=pytz.timezone('US/Pacific'))))
    #print("pd_prices",pd_prices)
    pd_prices = pd_prices.fillna(0)
    #energyPrices = pd_prices.customer_energy_charge.values + pd_prices.pdp_non_event_energy_credit.values + pd_prices.pdp_event_energy_charge.values
    energyPrices = pd_prices.customer_energy_charge.values + pd_prices.pdp_event_energy_charge.values
    # print('pd_prices.customer_energy_charge.values',pd_prices.customer_energy_charge.values)
    # print('pd_prices.pdp_non_event_energy_credit.values',pd_prices.pdp_non_event_energy_credit.values)
    # print('pd_prices.pdp_event_energy_charge.values',pd_prices.pdp_event_energy_charge.values)

    #cannot just add demand prices
    demandPrices = pd_prices.customer_demand_charge_season.values + pd_prices.pdp_non_event_demand_credit.values + pd_prices.customer_demand_charge_tou.values
    ##demand price increase not yet implemented
    # month_prior_start, month_prior_end = get_month_window(start_datetime.date(),time_delta=0)
    # month_prior_energy=get_df(site, month_prior_start, month_prior_end)
    # print('month energy', month_prior_energy['power'].max()) #check units
    # print('pdp energy', power_vector.max()) #check units
    #
    # if power_vector.max() > month_prior_energy['power'].max():
    #     increased_demand=power_vector.max()-month_prior_energy['power'].max()
    #     demand_charge=increased_demand*demandPrices
    #     print(demand_charge)

    return energyPrices @ energy_vector

def power_15min_to_hourly_energy(power_vector):
    energy_kwh = np.array(power_vector / 4.0) #TODO: Array or time-index series?
    result = pd.Series(np.sum(energy_kwh.reshape(-1, 4), axis=1))
    return result
