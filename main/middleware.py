import logging
from django.shortcuts import render

logger = logging.getLogger(__name__)

class Custom500Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            logger.error("Server error occurred", exc_info=True)
            return render(request, '404_error.html', status=500)
