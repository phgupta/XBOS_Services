__author__ = "Pranav Gupta"
__email__ = "pranavhgupta@lbl.gov"

import grpc
import pandas as pd

import skyspark_pb2
import skyspark_pb2_grpc

# CHECK: Change port!
HOST_ADDRESS = 'localhost:1234'


def run():

    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel(HOST_ADDRESS) as channel:

        stub = skyspark_pb2_grpc.skysparkStub(channel)

        try:
            query = 'readAll(id==@216fce5f-0d543013).hisRead(date(2019,06,30)..date(2019,07,01), {limit: null})'

            # Make remote procedure call
            response = stub.GetDataFromSkyspark(skyspark_pb2.Request(query=query))

            # Convert response object into pd.DataFrame()
            df = pd.DataFrame()
            for point in response.data:
                df = df.append([[point.time, point.value]])
            df.columns = ['datetime', 'power']
            df.set_index('datetime', inplace=True)
        except grpc.RpcError as e:
            print('client.py ERROR: \n', e)


if __name__ == '__main__':
    run()
