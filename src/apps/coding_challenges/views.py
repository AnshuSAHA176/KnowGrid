from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser,IsAuthenticated
from rest_framework import status,generics,viewsets
from .models import CodingChallenge,TestCase,Submission
from .serializer import CodingChallengTitleSerializer,CodingChallengSerializer
# 

class ChallengesView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        codingchallenges = CodingChallenge.objects.filter(
            video__youtube_id = self.kwargs.get('youtube_id'),
        )
        serializer = CodingChallengSerializer(codingchallenges,many=True)

        return Response(serializer.data)
    def get(self,request,challang_id):
        codingchallenges = CodingChallenge.objects.filter(
                    id = challang_id,

                )
        serializer = CodingChallengSerializer(codingchallenges)
        return Response(serializer.data)
