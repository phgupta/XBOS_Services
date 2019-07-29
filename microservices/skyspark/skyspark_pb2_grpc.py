# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

import skyspark_pb2 as skyspark__pb2


class skysparkStub(object):
  """RPC definition.
  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.GetDataFromSkyspark = channel.unary_unary(
        '/skyspark.skyspark/GetDataFromSkyspark',
        request_serializer=skyspark__pb2.Request.SerializeToString,
        response_deserializer=skyspark__pb2.Reply.FromString,
        )


class skysparkServicer(object):
  """RPC definition.
  """

  def GetDataFromSkyspark(self, request, context):
    """A simple RPC.
    An error is returned if there is no data for the given request.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_skysparkServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'GetDataFromSkyspark': grpc.unary_unary_rpc_method_handler(
          servicer.GetDataFromSkyspark,
          request_deserializer=skyspark__pb2.Request.FromString,
          response_serializer=skyspark__pb2.Reply.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'skyspark.skyspark', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
