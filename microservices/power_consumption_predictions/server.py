""" gRPC Server & client examples - https://grpc.io/docs/tutorials/basic/python.html """

import time
import grpc
import pytz
import json
import datetime
import pickle
import pandas as pd
from concurrent import futures
import xbos_services_getter

import power_consumption_predictions_pb2
import power_consumption_predictions_pb2_grpc

# CHECK: Change port!
HOST_ADDRESS = 'localhost:1234'
_ONE_DAY_IN_SECONDS = 60 * 60 * 24
_ONE_HOUR_IN_SECONDS = 60 * 60
UTC_TZ = pytz.timezone('UTC')
PT_TZ = pytz.timezone('US/Pacific')


class PowerConsumptionPredictionsServicer(power_consumption_predictions_pb2_grpc.PowerConsumptionPredictionsServicer):

    def __init__(self):
        """ Constructor. """

        self.model_folder = 'models/'
        self.model_info = None          # json file data

        self.building_name = None
        self.window = None
        self.end_time = None
        self.map_zone_state = {}

        self.zones = None
        self.curr_time_rounded = None   # Current time rounded down to 'window' min
        self.start_time = None          # Start time of first of num_timesteps required for prediction

        # List of zones in building
        self.building_zone_names_stub = xbos_services_getter.get_building_zone_names_stub()
        self.supported_buildings = xbos_services_getter.get_buildings(self.building_zone_names_stub)

    @staticmethod
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

    def rearrange_columns(self):
        """ Helper function to return ordered list according to json file specifications.

        Note
        ----
        1. This can be optimized and generalized to any json object.

        Returns
        -------
        list(str)
            List of columns in the correct order.

        """

        dic = self.model_info['features']
        new_dic = {}

        for key, value in dic.items():
            if type(value) == dict:
                if key == 'iat':
                    for key1, value1, in value.items():
                        new_dic['iat-' + key1] = value1
                else:
                    for key1, value1 in value.items():
                        new_dic[key1] = value1
            else:
                new_dic[key] = value

        return sorted(new_dic, key=new_dic.get)

    def add_time_features(self, data):
        """ Add time features to dataframe.

        Parameters
        ----------
        data    : pd.DataFrame()
            Dataframe to add time features to.

        Returns
        -------
        pd.DataFrame()
            Dataframe with time features added as columns.

        """

        with open(self.model_folder + self.building_name + '-model.json') as json_file:

            model_info = json.load(json_file)
            dic = model_info['features']['time_features']

            var_to_expand = []
            for key in dic.keys():
                if key == 'year':
                    data["year"] = data.index.year
                    var_to_expand.append("year")
                if key == 'month':
                    data["month"] = data.index.month
                    var_to_expand.append("month")
                if key == 'week':
                    data["week"] = data.index.week
                    var_to_expand.append("week")
                if key == 'weekday':
                    data["weekday"] = data.index.weekday
                    var_to_expand.append("weekday")
                if key == 'hour':
                    data["hour"] = data.index.hour
                    var_to_expand.append("hour")

            # # One-hot encode the time features
            # for var in var_to_expand:
            #     add_var = pd.get_dummies(data[var], prefix=var, drop_first=True)
            #
            #     # Add all the columns to the model data
            #     data = data.join(add_var)
            #
            #     # Drop the original column that was expanded
            #     data.drop(columns=[var], inplace=True)

        return data

    def train_ciee(self):
        """ Training model for CIEE building. """
        # Do hyper-parameter training for LSTM/RF and save the model in a pickle file
        pass

    def add_oat(self, data):
        """ Add outdoor air temperature to dataframe.

        Parameters
        ----------
        data    : pd.DataFrame()
            Dataframe to add OAT to.

        Returns
        -------
        pd.DataFrame()
            Dataframe with OAT of zones added as columns.

        """

        outdoor_historic_stub = xbos_services_getter.get_outdoor_temperature_historic_stub()
        historic_oat = xbos_services_getter.get_preprocessed_outdoor_temperature(outdoor_historic_stub,
                                                                                 building=self.building_name,
                                                                                 start=self.start_time,
                                                                                 end=self.curr_time_rounded,
                                                                                 window=str(self.window)+'m')

        outdoor_prediction_stub = xbos_services_getter.get_outdoor_temperature_prediction_stub()
        predicted_oat = xbos_services_getter.get_outdoor_temperature_prediction(outdoor_prediction_stub,
                                                                                building=self.building_name,
                                                                                start=datetime.datetime.today()
                                                                                + datetime.timedelta(seconds=1),
                                                                                end=self.end_time.replace(tzinfo=PT_TZ),
                                                                                window=str(self.window)+'m')

        data = data.join(historic_oat['temperature'])
        data = data.merge(predicted_oat[['temperature']], on='temperature', how='outer',
                          left_index=True, right_index=True)

        return data

    def add_zone_states(self, data):
        """ Add each of the zones' HVAC states.

        Parameters
        ----------
        data    : pd.DataFrame()
            Dataframe to add zones' HVAC states to.

        Returns
        -------
        pd.DataFrame()
            Dataframe with HVAC states added as columns.

        """

        dic = self.model_info['features']['zones']
        for key in dic.keys():

            # prev_minutes to curr_time historic data
            indoor_historic_stub = xbos_services_getter.get_indoor_historic_stub()
            historic_states = xbos_services_getter.get_indoor_actions_historic(indoor_historic_stub,
                                                                               building=self.building_name,
                                                                               zone=key,
                                                                               start=self.start_time,
                                                                               end=self.curr_time_rounded,
                                                                               window=str(self.window)+'m',
                                                                               agg='MAX')

            print('historic_states: ', historic_states)
            print('data before joining: \n', data.head())

            # Join historic HVAC zone states
            data = data.join(historic_states)

            print('data after joining: \n', data.head())

        print('data: \n', data.head())

        # curr_time to future_minutes (user inputted data)
        for zone, states in self.map_zone_state.items():
            data.loc[self.curr_time_rounded:self.end_time, zone] = states

        return data

    # def add_iat(self, data):
    #     """ Add indoor air temperature to dataframe.
    #
    #     Parameters
    #     ----------
    #     data    : pd.DataFrame()
    #         Dataframe to add IAT to.
    #
    #     Returns
    #     -------
    #     pd.DataFrame()
    #         Dataframe with IAT of zones added as columns.
    #
    #     """
    #
    #     dic = self.model_info['features']['iat']
    #     for key in dic.keys():
    #
    #         # prev_minutes to curr_time historic data
    #         indoor_historic_stub = xbos_services_getter.get_indoor_historic_stub()
    #         historic_iat = xbos_services_getter.get_indoor_temperature_historic(indoor_historic_stub,
    #                                                                             building=self.building_name,
    #                                                                             zone=key,
    #                                                                             start=self.start_time,
    #                                                                             end=self.curr_time_rounded,
    #                                                                             window=self.window,
    #                                                                             agg='MEAN')
    #
    #         # curr_time to future_minutes predicted data
    #         indoor_temperature_prediction_stub = xbos_services_getter.get_indoor_temperature_prediction_stub()
    #         predicted_iat = xbos_services_getter.get_indoor_temperature_prediction(indoor_temperature_prediction_stub,
    #                                                                                building=self.building_name,
    #                                                                                zone=key,
    #                                                                                current_time=self.curr_time_rounded,
    #                                                                                action, t_in, t_out, t_prev,
    #                                                                                other_zone_temperatures)
    #
    #         # Add iat to data
    #
    #     return data

    def create_testing_dataframe(self):
        """ Create test dataframe to be used for model prediction.

        Returns
        -------
        pd.DataFrame()
            Dataframe used for making predictions into the future.

        """

        # Create empty dataframe with correct indices
        indices = pd.date_range(start=self.curr_time_rounded, freq=str(self.window)+'T', end=self.end_time)
        x_test = pd.DataFrame(index=indices)

        # CHECK: Add IAT
        # x_test = self.add_iat(x_test)

        # Add zone states
        x_test = self.add_zone_states(x_test)

        # Add OAT
        x_test = self.add_oat(x_test)

        # Add time features such as hour, day of week, etc.
        x_test = self.add_time_features(x_test)

        # print('x_test: \n', x_test.head())

        # CHECK: Rearrange columns of dataframe according to .json file specifications.
        x_test.columns = self.rearrange_columns()

        return x_test

    def predictions(self):
        """ Retrieve saved model weights and make predictions.

        Returns
        -------
        gRPC response
            List of points containing the datetime and power consumption prediction.

        """

        # Round down to the nearest 5min mark.
        # Example: If current time is 17:47, round down to 17:45 and then make predictions!
        date_today = datetime.datetime.today()
        self.curr_time_rounded = self.round_minutes(UTC_TZ.localize(date_today), 'down', self.window)

        # Calculate start time of testing dataframe
        self.start_time = self.curr_time_rounded - datetime.timedelta(minutes=self.model_info['num_prev_minutes'])

        x_test = self.create_testing_dataframe()

        loaded_model = pickle.load(open(self.model_folder + self.building_name + '-model.sav', 'rb'))
        y_pred = loaded_model.predict(x_test)

        result = []
        for i in range(len(y_pred)):

            tim = self.curr_time_rounded + datetime.timedelta(minutes=i*self.model_info['freq_minutes'])
            tim = time.strftime('%Y-%m-%d %H:%M:%S')

            point = power_consumption_predictions_pb2.Reply.PowerConsumptionPredictionPoint(time=tim, power=y_pred[i])
            result.append(point)

        return power_consumption_predictions_pb2.Reply(point=result)

    def retrain(self):
        """ Retrain model of building with updated data. """

        # Dictionary that maps building name to training model function
        # Add more key, value pairs as the number of buildings increase
        retrain_bldg = {
            'ciee': self.train_ciee
        }

        try:
            retrain_bldg[self.building_name]
        except KeyError as e:
            print(e)

    def get_parameters(self, request):
        """ Storing and error checking request parameters.

        Parameters
        ----------
        request     : gRPC request
            Contains parameters to fetch data.

        Returns
        -------
        str
            Error message.

        """

        # Retrieve parameters from gRPC request object
        self.building_name = request.building
        self.end_time = datetime.datetime.utcfromtimestamp(float(request.end/1e9)).replace(tzinfo=pytz.utc)

        if request.window[-1] != 'm':
            return "invalid request, window can be only in min. correct format: \'15m\', \'5m\'..."
        self.window = int(request.window[:-1])

        for dic in request.map_zone_state:
            self.map_zone_state[dic.zone] = dic.state

        if any(not elem for elem in [self.building_name, self.window, self.map_zone_state]):
            return "invalid request, empty param(s)"

        if request.building not in self.supported_buildings:
            return "invalid request, building not found, supported buildings:" + str(self.supported_buildings)

        self.zones = xbos_services_getter.get_zones(self.building_zone_names_stub, self.building_name)

        if set(self.map_zone_state.keys()) != set(self.zones):
            return "invalid request, specify all zones and their states in the building."

        # Add error checking for window

        if request.end < time.time():
            return "invalid request, end time has to be in the future"

        with open(self.model_folder + self.building_name + '-model.json') as json_file:
            self.model_info = json.load(json_file)

            if self.end_time > self.round_minutes(UTC_TZ.localize(datetime.datetime.today()), 'down', self.window) + \
                    datetime.timedelta(minutes=self.model_info['num_future_minutes']):
                return "invalid request, end date is further than what model can predict"

        # # Other error checkings
        # duration = utils.get_window_in_sec(request.window)
        # if duration <= 0:
        #     return None, "invalid request, duration is negative or zero"
        # if request.start + (duration * 1e9) > request.end:
        #     return None, "invalid request, start date + window is greater than end date"

        return

    def get_power_predictions(self, request):
        """ Main function of micro-service. This function does error checking of request parameters and
        decides if the model for given building needs to be re-trained or not.

        Parameters
        ----------
        request     : gRPC request
            Contains parameters to fetch data.

        Returns
        -------
        pd.DataFrame, str
            Dataframe with predictions, error message.

        """

        error = self.get_parameters(request)
        if error:
            return None, error

        retraining_period = datetime.timedelta(days=14)
        date_today = datetime.datetime.today()
        last_trained_date = datetime.datetime.utcfromtimestamp(self.model_info['last_trained'])
        delta = date_today - last_trained_date

        # Check if time passed since last update has been more than the retraining_period
        if delta >= retraining_period:
            self.retrain()
        self.predictions()

    def GetPowerConsumptionPredictions(self, request, context):
        """

        Parameters
        ----------
        request     : gRPC request
            Contains parameters to fetch data.
        context     : ???
            ???

        Returns
        -------
        gRPC response
            List of points containing the datetime and power consumption.

        """

        result, error = self.get_power_predictions(request)
        if error:
            # List of status codes: https://github.com/grpc/grpc/blob/master/doc/statuscodes.md
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(error)
            return power_consumption_predictions_pb2.Reply()

        return result


if __name__ == '__main__':

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    power_consumption_predictions_pb2_grpc.add_PowerConsumptionPredictionsServicer_to_server(
        PowerConsumptionPredictionsServicer(), server
    )
    server.add_insecure_port(HOST_ADDRESS)
    server.start()

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)
