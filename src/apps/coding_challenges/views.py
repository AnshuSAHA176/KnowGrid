
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from .models import CodingChallenge,Submission
from .serializer import (
    CodingChallengSerializer,
    CodingChallengTitleSerializer,
    SubmissionSerializer,
    SubmissionViewSerializer
)
from rest_framework.response import Response
from .runner_test import execute_code


class ChallengesView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CodingChallenge.objects.select_related('user','challenge')

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


class SubmissionView(generics.ListCreateAPIView):
    permission_classes=[IsAuthenticated]
    queryset = Submission.objects.all()
    
    lookup_field='challenge_id'
    lookup_url_kwarg='challenge_id'
    def get_serializer_class(self):
        if self.request.method =='POST':
            return SubmissionSerializer
        return SubmissionViewSerializer
    def post(self, request, *args, **kwargs):
        serializer= self.get_serializer(data=self.request.data,context={'request':self.request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        execute_code.delay(instance.id) 
        return Response(serializer.data)