from .base import *

SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] = timedelta(days=1)

# SILKY_PYTHON_PROFILER = True
# SILKY_PYTHON_PROFILER_BINARY = True
# SILKY_AUTHENTICATION = True  # Require login to view profiling
# SILKY_AUTHORISATION = True


# Use SILKY_INTERCEPT_FUNC for pattern-based path ignoring (supports wildcards)
def should_intercept_request(request):
    """
    Return True if the request should be profiled, False to ignore it.
    """
    path = request.path_info

    # Ignore paths that start with these patterns
    ignore_patterns = [
        "/admin/",
        "/static/",
        "/media/",
        "/silk/",
    ]

    # Ignore specific files
    ignore_files = [
        "/favicon.ico",
        "/robots.txt",
    ]

    # Check if path starts with any ignore pattern
    for pattern in ignore_patterns:
        if path.startswith(pattern):
            return False

    # Check if path matches any ignore file
    if path in ignore_files:
        return False

    return True


SILKY_INTERCEPT_FUNC = should_intercept_request

INSTALLED_APPS += ["silk"]

MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]
