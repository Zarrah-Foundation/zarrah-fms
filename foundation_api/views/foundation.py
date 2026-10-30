from rest_framework.views import APIView
from foundation_api.serializers.foundation import FoundationSerializer
from foundation_api.services.foundation import FoundationService
from foundation_api.utils import api_response


class FoundationAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        settings = FoundationService.get_settings()
        serializer = FoundationSerializer(
            settings,
            context={"request": request},
        )
        return api_response(serializer.data)