# your_project/custom_silk_middleware.py

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from silk.middleware import SilkyMiddleware


class CustomSilkyMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.get_response = get_response
        self._silky = SilkyMiddleware(get_response)

    def __call__(self, request):
        ignore_paths = getattr(settings, "SILKY_IGNORE_PATHS", [])
        request_path = request.path_info

        # Skip profiling if any pattern matches
        if any(ignored in request_path for ignored in ignore_paths):
            return self.get_response(request)

        # Else, let Silk handle it
        return self._silky(request)
