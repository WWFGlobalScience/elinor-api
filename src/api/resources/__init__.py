from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from rest_framework.views import Response, exception_handler
from rest_framework import status


def api_exception_handler(exc, context):
    # Call REST framework's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    # catch designated otherwise-500-level exceptions if the error response hasn't already been generated
    if response is None:
        message = None
        if isinstance(exc, ProtectedError):
            message = exc.__str__()
        if isinstance(exc, ValidationError):
            message = exc.message_dict
        if message:
            response = Response(
                {"message": message}, status=status.HTTP_400_BAD_REQUEST
            )

    return response
