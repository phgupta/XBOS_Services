import grpc
import pytz
import datetime
import pandas as pd

import power_consumption_predictions_pb2
import power_consumption_predictions_pb2_grpc

# CHECK: Change port!
HOST_ADDRESS = 'localhost:1234'


def run():

    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel(HOST_ADDRESS) as channel:

        stub = power_consumption_predictions_pb2_grpc.PowerConsumptionPredictionsStub(channel)

        try:

            utc_tz = pytz.timezone('UTC')
            end_date = utc_tz.localize(datetime.datetime.today() + datetime.timedelta(minutes=5))
            end_date = end_date.replace(microsecond=0)
            end = int(end_date.timestamp() * 1e9)

            bldg = "ciee"
            window = '5m'

            # Specify all zones and their state values.
            dic = {
                'hvac_zone_centralzone': [1, 1, 1],
                'hvac_zone_eastzone': [0, 0, 0],
                'hvac_zone_northzone': [0, 0, 0],
                'hvac_zone_southzone': [0, 0, 0]
            }

            lst1, lst2 = [], []
            for key, value in dic.items():
                for num in value:
                    lst1.append(power_consumption_predictions_pb2.Request.Dict.State(state=num))
                    lst2.append(power_consumption_predictions_pb2.Request.Dict(zone=key, state=lst1))

            # Create gRPC request object
            request = power_consumption_predictions_pb2.Request(
                building=bldg,
                end=end,
                window=window,
                map_zone_state=lst2
            )

            response = stub.GetPowerConsumptionPredictions(request)

            df = pd.DataFrame()
            for point in response.point:
                df = df.append([[point.time, point.power]])

            df.columns = ['datetime', 'power']
            df.set_index('datetime', inplace=True)
            df.to_csv(bldg + '-predictions.csv')

        except grpc.RpcError as e:
            print(e)


if __name__ == '__main__':

    run()
