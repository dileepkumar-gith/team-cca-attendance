class NoCacheForAuthenticatedPagesMiddleware:
    """
    Tells the browser never to cache pages viewed while logged in.
    This closes a real security gap: without this, pressing the browser's
    Back button after logout could show a stale, cached copy of a protected
    page (e.g. the dashboard) without the browser re-checking with the server
    that the session is still valid.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
        return response