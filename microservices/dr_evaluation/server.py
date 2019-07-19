__author__ = "Pranav Gupta"
__email__ = "pranavhgupta@lbl.gov"

""" gRPC Server & client examples - https://grpc.io/docs/tutorials/basic/python.html """

import time
import pytz
import grpc
from concurrent import futures
from datetime import datetime

import xbos_services_getter
from dr_evaluation import evaluate

import dr_evaluation_pb2
import dr_evaluation_pb2_grpc

METER_DATA_HOST_ADDRESS = 'localhost:1234'
_ONE_DAY_IN_SECONDS = 60 * 60 * 24


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

        try:
            result = evaluate.evaluate(self.building, self.event_day, model_name=self.model_name)

            return dr_evaluation_pb2.Reply(
                building=result['site'],
                event_day=result['date'].strftime('%Y-%m-%d %H:%M:%S'),
                cost=dr_evaluation_pb2.Cost(actual=result['energy cost']['baseline'],
                                            baseline=result['energy cost']['baseline']),
                oat_mean=dr_evaluation_pb2.OAT_Mean(event=result['OAT_mean']['event'],
                                                    baseline=result['OAT_mean']['baseline']),
                baseline_type=result['baseline-type'],
                baseline_rmse=result['baseline-rmse'],
                actual=result['actual'],
                baseline=result['baseline']
            ), None
        except Exception as e:
            return None, e

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
