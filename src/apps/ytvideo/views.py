from rest_framework import generics
from .models import YtVideo, YtVideoChunks
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializer import (
    VideoCreateSerializer,
    VideoTitleSerializer,
    VideoChunksSerializer,
)
from django.db import IntegrityError
from rest_framework.views import APIView
from pgvector.django import CosineDistance
from .RAG.generate_embedding import user_embedding_generator
from .RAG.crag import crag
from .models import Conversation
from django.shortcuts import get_object_or_404


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


class RetriveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, youtube_id,conversation_id):
        try:
            message = request.data["message"]
        except KeyError:
            return Response(
                {"error": "Please follow this stucture {'message':'your query'}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if conversation_id:
            conversation = get_object_or_404(Conversation,id=conversation_id,video_id=youtube_id,user=request.user)
        else:
            conversation = Conversation.objects.create(
                user=request.user,
                video = youtube_id,
                 messages=[],
            )

        result = crag().invoke(
            {
                "user_query": message,
                "youtube_id": youtube_id,
            }
        )
        return Response({"response": result["answer"]})
