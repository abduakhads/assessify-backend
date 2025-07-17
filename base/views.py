import requests
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status


# Create your views here.
@api_view(["GET"])
def activate_user(request, uidb64, token):
    base_url = request.build_absolute_uri("/").rstrip("/")
    internal_url = f"{base_url}/auth/users/activation/"
    payload = {"uid": uidb64, "token": token}
    try:
        internal_response = requests.post(internal_url, json=payload)
        if internal_response.status_code == 204:
            return Response(
                {"detail": "User activated successfilly"}, status=status.HTTP_200_OK
            )
        else:
            try:
                data = internal_response.json()
            except ValueError:
                data = {"error": "An error occurred while activating the user."}
            return Response(data, status=internal_response.status_code)
    except requests.RequestException as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
