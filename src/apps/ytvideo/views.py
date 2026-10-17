from rest_framework import generics

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializer import VideoCreateSerializer

class VideoView(generics.ListCreateAPIView):
    permission_classes=[IsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        if self.request.method == "POST":
            return VideoCreateSerializer(data = self.request.data,context={"request":self.request})
        return 