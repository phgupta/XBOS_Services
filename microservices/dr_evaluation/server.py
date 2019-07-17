__author__ = "Pranav Gupta"
__email__ = "pranavhgupta@lbl.gov"

""" gRPC Server & client examples - https://grpc.io/docs/tutorials/basic/python.html """

import time
import pytz
import grpc
from concurrent import futures
from datetime import datetime

import xbos_services_getter
from main import evaluate

import dr_evaluation_pb2
import dr_evaluation_pb2_grpc

# METER_DATA_HOST_ADDRESS = os.environ["METER_DATA_HISTORICAL_HOST_ADDRESS"]
METER_DATA_HOST_ADDRESS = 'localhost:1234'
_ONE_DAY_IN_SECONDS = 60 * 60 * 24


# def get_meter_data(pymortar_client, pymortar_objects, site, start, end,
#                    point_type="Green_Button_Meter", agg='MEAN', window='15m'):
#     """ Get meter data from pymortar.
#
#     Parameters
#     ----------
#     pymortar_client     : pymortar.Client({})
#         Pymortar Client Object.
#     pymortar_objects    : dict
#         Dictionary that maps aggregation values to corresponding pymortar objects.
#     site                : str
#         Building name.
#     start               : str
#         Start date - 'YYYY-MM-DDTHH:MM:SSZ'
#     end                 : str
#         End date - 'YYYY-MM-DDTHH:MM:SSZ'
#     point_type          : str
#         Type of data, i.e. Green_Button_Meter, Building_Electric_Meter...
#     agg                 : str
#         Values include MEAN, MAX, MIN, COUNT, SUM, RAW (the temporal window parameter is ignored)
#     window              : str
#         Size of the moving window.
#
#     Returns
#     -------
#     pd.DataFrame(), defaultdict(list)
#         Meter data, dictionary that maps meter data's columns (uuid's) to sitenames.
#
#     """
#
#     agg = pymortar_objects.get(agg, 'ERROR')
#
#     if agg == 'ERROR':
#         raise ValueError('Invalid aggregate type; should be string and in caps; values include: ' +
#                          pymortar_objects.keys())
#
#     query_meter = "SELECT ?meter WHERE { ?meter rdf:type brick:" + point_type + " };"
#
#     # Define the view of meters (metadata)
#     meter = pymortar.View(
#         name="view_meter",
#         sites=[site],
#         definition=query_meter
#     )
#
#     # Define the meter timeseries stream
#     data_view_meter = pymortar.DataFrame(
#         name="data_meter",  # dataframe column name
#         aggregation=agg,
#         window=window,
#         timeseries=[
#             pymortar.Timeseries(
#                 view="view_meter",
#                 dataVars=["?meter"]
#             )
#         ]
#     )
#
#     # Define timeframe
#     time_params = pymortar.TimeParams(
#         start=start,
#         end=end
#     )
#
#     # Form the full request object
#     request = pymortar.FetchRequest(
#         sites=[site],
#         views=[meter],
#         dataFrames=[data_view_meter],
#         time=time_params
#     )
#
#     # Fetch data from request
#     response = pymortar_client.fetch(request)
#
#     # resp_meter = (url, uuid, sitename)
#     resp_meter = response.query('select * from view_meter')
#
#     # Map's uuid's to the site names
#     map_uuid_sitename = defaultdict(list)
#     for (url, uuid, sitename) in resp_meter:
#         map_uuid_sitename[uuid].append(sitename)
#
#     return response['data_meter'], map_uuid_sitename
#
#
# def get_historical_data(request, pymortar_client, pymortar_objects):
#     """ Get historical meter data using pymortar and create gRPC repsonse object.
#
#     Parameters
#     ----------
#     request                 : gRPC request
#         Contains parameters to fetch data.
#     pymortar_client     : pymortar.Client({})
#         Pymortar Client Object.
#     pymortar_objects    : dict
#         Dictionary that maps aggregation values to corresponding pymortar objects.
#
#     Returns
#     -------
#     gRPC response, str
#         List of points containing the datetime and power consumption; Error Message
#
#     """
#
#     start_time = datetime.utcfromtimestamp(float(request.start / 1e9)).replace(tzinfo=pytz.utc)
#     end_time = datetime.utcfromtimestamp(float(request.end / 1e9)).replace(tzinfo=pytz.utc)
#
#     try:
#         df, map_uuid_meter = get_meter_data(pymortar_client=pymortar_client,
#                                             pymortar_objects=pymortar_objects,
#                                             site=request.building,
#                                             point_type=request.point_type,
#                                             start=start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
#                                             end=end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
#                                             agg=request.aggregate,
#                                             window=request.window)
#     except Exception as e:
#         return None, e
#
#     if len(df.columns) == 2:
#         df[df.columns[0]] = df[df.columns[0]] + df[df.columns[1]]
#         df = df.drop(columns=[df.columns[1]])
#
#     df.columns = ['power']
#
#     result = []
#     for index, row in df.iterrows():
#         point = dr_evaluation_pb2.MeterDataPoint(time=int(index.timestamp()*1e9), power=row['power'])
#         result.append(point)
#
#     return dr_evaluation_pb2.Reply(point=result), None


class DREvaluationServicer(dr_evaluation_pb2_grpc.DREvaluationServicer):

    def __init__(self):
        """ Constructor - store class variables. """

        # Request parameters
        self.building = None
        self.event_day = None
        self.model_name = None

        # List of buildings
        building_names_stub = xbos_services_getter.get_building_zone_names_stub()
        self.supported_buildings = xbos_services_getter.get_buildings(building_names_stub)

    def get_parameters(self, request):
        """ Storing and error checking request parameters.

        Parameters
        ----------
        request                 : gRPC request
            Contains parameters to fetch data.

        Returns
        -------
        str
            Error message. If no error message, then return None.

        """

        self.building = request.building
        self.event_day = request.event_day
        self.model_name = request.model_name

        if any(not elem for elem in [self.building, self.event_day]):
            return "invalid request, empty param(s)"

        if not self.model_name:
            self.model_name = 'best'

        self.event_day = datetime.utcfromtimestamp(float(self.event_day / 1e9)).replace(tzinfo=pytz.utc)

        if self.building not in self.supported_buildings:
            return "invalid request, building not found; supported buildings: " + str(self.supported_buildings)

        return None

    def evaluate(self):
        """ Evaluate the DR day and make response object.

        Returns
        -------
        dr_evaluation_pb2.Reply(), str
            Result, Error Message

        """

        result = evaluate.evaluate(self.building, self.event_day, model_name=self.model_name)
        print('RESULT: \n', result)

        return dr_evaluation_pb2.Reply(
            building='ciee',
            event_day='28th June, 2019',
            cost=dr_evaluation_pb2.Cost(actual=10.8, baseline=33.5),
            oat_mean=dr_evaluation_pb2.OAT_Mean(event=56.2, baseline=234.3),
            baseline_type='dasf',
            baseline_rmse=4534.1,
            actual=[56.3, 65.3],
            baseline=[11.1, 112.6]
        )

    def GetDREvaluation(self, request, context):
        """ RPC.

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

        error = self.get_parameters(request)
        if error:
            # List of status codes: https://github.com/grpc/grpc/blob/master/doc/statuscodes.md
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(error)
            return dr_evaluation_pb2.Reply()
        else:
            result, error = self.evaluate()
            if error:
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details(error)
                return dr_evaluation_pb2.Reply()
        return result


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    dr_evaluation_pb2_grpc.add_DREvaluationServicer_to_server(DREvaluationServicer(), server)
    server.add_insecure_port(METER_DATA_HOST_ADDRESS)
    server.start()
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()
