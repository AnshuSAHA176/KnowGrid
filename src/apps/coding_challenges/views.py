
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import CodingChallenge
from .serializer import (
    CodingChallengSerializer,
    CodingChallengTitleSerializer,
)


class ChallengesView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CodingChallenge.objects.all()

        youtube_id = self.kwargs.get("youtube_id")

        if youtube_id:
            queryset = queryset.filter(
                video__youtube_id=youtube_id
            )

        return queryset.prefetch_related("testcases")

    def get_serializer_class(self):
        if self.action == "list":
            return CodingChallengTitleSerializer

        return CodingChallengSerializer
