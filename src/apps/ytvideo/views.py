from rest_framework import generics
from .models import YtVideo
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializer import VideoCreateSerializer, VideoTitleSerializer
from django.db import IntegrityError


class VideoView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return YtVideo.objects.select_related("user").filter(user=self.request.user)

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method == "POST":
            return VideoCreateSerializer
        return VideoTitleSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(
                data=self.request.data, context={"request": self.request}
            )
            serializer.is_valid(raise_exception=True)
            video = serializer.save()
            return Response(
                {
                    "youtube_id": video.youtube_id,
                    "status": video.status,
                    "message": "Video queued for processing.",
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except IntegrityError:
            return Response(
                {"error": "Url already procced. You can search for it"},
                status=status.HTTP_409_CONFLICT,
            )
