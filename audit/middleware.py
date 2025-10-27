import threading


_state = threading.local()


def get_current_user():
    return getattr(_state, 'current_user', None)


class CurrentUserMiddleware:
    """Stores the authenticated user in thread-local storage for signals to access."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _state.current_user = getattr(request, 'user', None)
        try:
            response = self.get_response(request)
        finally:
            # Clean up to avoid leakage across requests (important on long-lived threads)
            _state.current_user = None
        return response