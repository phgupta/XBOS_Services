__author__ = "Pranav Gupta"
__email__ = "pranavhgupta@lbl.gov"

import pytz
import grpc
import datetime

import dr_evaluation_pb2
import dr_evaluation_pb2_grpc

# CHECK: Change port!
METER_DATA_HOST_ADDRESS = 'localhost:1234'


def run():

    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel(METER_DATA_HOST_ADDRESS) as channel:

        stub = dr_evaluation_pb2_grpc.DREvaluationStub(channel)

        try:

            building = 'local-butcher-shop'
            model_name = 'best'

            utc_tz = pytz.timezone('UTC')
            event_day = utc_tz.localize(datetime.datetime(2018, 7, 16)).replace(microsecond=0)
            event_day = int(event_day.timestamp() * 1e9)

            # Create gRPC request object
            request = dr_evaluation_pb2.Request(
                building=building,
                model_name=model_name,
                event_day=event_day
            )

            # Execute RPC
            response = stub.GetDREvaluation(request)

            # Store results into a dictionary
            result = {}
            result['building'] = response.building
            result['event_day'] = response.event_day

            result['cost'] = {}
            result['cost']['actual'] = [response.cost.actual]
            result['cost']['baseline'] = response.cost.baseline

            result['oat_mean'] = {}
            result['oat_mean']['event'] = response.oat_mean.event
            result['oat_mean']['baseline'] = response.oat_mean.baseline

            result['baseline_type'] = response.baseline_type
            result['baseline_rmse'] = response.baseline_rmse
            result['actual'] = response.actual
            result['baseline'] = response.baseline

            print(result)

        except grpc.RpcError as e:
            print(e)


if __name__ == '__main__':
    run()
