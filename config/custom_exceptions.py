from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, ValidationError):
        error_message = exc.detail.get("non_field_errors", [""])[0]

        if error_message == "The fields question, text must make a unique set.":
            error_message = "This answer already exists for this question."
        return Response(
            {
                "detail": error_message,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return response
