from django.http import Http404


class StaffOnlyAdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            if not (request.user.is_authenticated and request.user.is_staff):
                raise Http404("Page not found")

        response = self.get_response(request)
        return response
