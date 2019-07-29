__author__ = "Pranav Gupta"
__email__ = "pranavhgupta@lbl.gov"

""" gRPC Server & client examples - https://grpc.io/docs/tutorials/basic/python.html """

import time
import grpc
import pytz
import numpy as np
from concurrent import futures
from spyspark import spyspark_client

import skyspark_pb2
import skyspark_pb2_grpc

# CHECK: Change port!
HOST_ADDRESS = 'localhost:1234'
_ONE_DAY_IN_SECONDS = 60 * 60 * 24
_ONE_HOUR_IN_SECONDS = 60 * 60
UTC_TZ = pytz.timezone('UTC')
PT_TZ = pytz.timezone('US/Pacific')


class skysparkServicer(skyspark_pb2_grpc.skysparkServicer):

    def __init__(self):
        """ Constructor. """

        self.query = None

        # Client that will be used to call all functions for SkySpark class
        self.client = spyspark_client("URL")

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

        self.query = request.query
        if not self.query:
            return "invalid request, query parameter empty"
        if not isinstance(self.query, str):
            return "invalid request, query must be a string; " \
                   "example query: readAll(id==@abcd1234).hisRead(date(2010,01,01)..date(2019,07,01), {limit: null})"
        return

    def _get_skyspark_data(self):
        """ Query skyspark and retrieve data.

        Returns
        -------
        pd.Dataframe, str
            Result dataframe, error message

        """

        try:
            df = self.client.query(self.query)
        except Exception as e:
            return None, "Invalid query or failure in skyspark connection; Error: {0}".format(str(e))

        result = []
        for index, row in df.iterrows():
            tim = index.strftime('%Y-%m-%d %H:%M:%S')
            val = float(row.values) if not np.isnan(row.values) else 0.0    # Convert all NaN values to 0.0
            result.append(skyspark_pb2.Data(time=tim, value=val))
        return skyspark_pb2.Reply(data=result), None

    def get_skyspark_data(self, request):
        """ Main function of micro-service; checks for errors in the request parameter(s) and queries for
        data from skyspark.


        Parameters
        ----------
        request     : gRPC request
            Contains parameters to fetch data.

        Returns
        -------
        pd.DataFrame, str
            Dataframe, error message.

        """

        error = self.get_parameters(request)
        if error:
            return None, error
        else:
            result, error = self._get_skyspark_data()
            if error:
                return None, error
        return result, None

    def GetDataFromSkyspark(self, request, context):
        """ gRPC function.

        Parameters
        ----------
        request     : gRPC request
            Contains parameters to fetch data.
        context     : ???
            ???

        Returns
        -------
        gRPC response
            List of points containing the datetime and skyspark data.

        """

        result, error = self.get_skyspark_data(request)
        if error:
            # List of status codes: https://github.com/grpc/grpc/blob/master/doc/statuscodes.md
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(error)
            return skyspark_pb2.Data()
        return result


if __name__ == '__main__':

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    skyspark_pb2_grpc.add_skysparkServicer_to_server(skysparkServicer(), server)
    server.add_insecure_port(HOST_ADDRESS)
    server.start()
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)
