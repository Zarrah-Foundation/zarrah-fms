from rest_framework.response import Response

from foundation_api.version import API_VERSION


def api_response(data, success=True, status=200):
    return Response(
        {
            "success": success,
            "version": API_VERSION,
            "data": data,
        },
        status=status,
    )