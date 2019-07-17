__author__ = "Pranav Gupta"
__email__ = "pranavhgupta@lbl.gov"

import os
import pytz
import grpc
import datetime
import pandas as pd
from pathlib import Path

import sys
sys.path.append(str(Path.cwd().parent))

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
            # end_date = utc_tz.localize(datetime.datetime.today() + datetime.timedelta(minutes=5))
            # end_date = end_date.replace(microsecond=0)

            event_day = utc_tz.localize(datetime.datetime(2018, 7, 16)).replace(microsecond=0)
            event_day = int(event_day.timestamp() * 1e9)

            # Create gRPC request object
            request = dr_evaluation_pb2.Request(
                building=building,
                model_name=model_name,
                event_day=event_day
            )

            response = stub.GetDREvaluation(request)

            print("Response: ", response)

            # # NOTE
            # # Converting list(dic) to pd.DataFrame is significantly faster than appending a single row to pd.DataFrame.
            # row_list = []
            # for point in response.point:
            #     dic = {
            #         'datetime': point.time,
            #         'power': point.power
            #     }
            #     row_list.append(dic)
            #
            # df = pd.DataFrame(row_list)
            # df.set_index('datetime', inplace=True)
            #
            # # Store the dataframe in "data/" folder
            # data_folder = 'data'
            # if not os.path.exists(data_folder):
            #     os.makedirs(data_folder)
            # df.to_csv(data_folder + '/' + bldg + '.csv')

        except grpc.RpcError as e:
            print(e)


if __name__ == '__main__':
    run()
