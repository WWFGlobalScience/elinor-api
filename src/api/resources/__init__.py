from django.db.models.deletion import ProtectedError
from rest_framework.views import Response, exception_handler
from rest_framework import status


def api_exception_handler(exc, context):
    # Call REST framework's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    # catch designated otherwise-500-level exceptions if the error response hasn't already been generated
    if isinstance(exc, ProtectedError) and not response:
        response = Response(
            {"message": exc.__str__()}, status=status.HTTP_400_BAD_REQUEST
        )

    return response
