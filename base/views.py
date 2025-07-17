import requests
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status


from rest_framework import serializers


# Serializer for the response
class ActivateUserResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
    error = serializers.CharField(required=False)


# Create your views here.
@api_view(["GET"])
def activate_user(request, uidb64, token):
    base_url = request.build_absolute_uri("/").rstrip("/")
    internal_url = f"{base_url}/auth/users/activation/"
    payload = {"uid": uidb64, "token": token}
    try:
        internal_response = requests.post(internal_url, json=payload)
        if internal_response.status_code == 204:
            response_data = {"detail": "User activated successfilly"}
            serializer = ActivateUserResponseSerializer(data=response_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            try:
                data = internal_response.json()
            except ValueError:
                data = {"error": "Internal error occurred while activating the user."}
            serializer = ActivateUserResponseSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=internal_response.status_code)
    except requests.RequestException as e:
        response_data = {"error": str(e)}
        serializer = ActivateUserResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
