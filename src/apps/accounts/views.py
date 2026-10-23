from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User
from .serializer import RegisterSerializer, LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from apps.coding_challenges.models import Submission
from django.db.models import Count, Q, F
from apps.coding_challenges.serializer import SubmissionViewSerializer,ContinuLarningSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response({"access": str(access), "refresh": str(refresh)})


class Dashboard(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        submission = (
            Submission.objects.filter(user=request.user)
            .order_by("-created_at")
            .aggregate(
                challenges_solved=Count(
                    "id",
                    filter=Q(status=Submission.StatusChoices.ACCEPTED),
                ),
                total_submissions=Count("id"),
            )
        )

        continue_learning = Submission.objects.filter(
            user=request.user,
            status__in=[
                Submission.StatusChoices.FAILED,
                Submission.StatusChoices.PENDING,
            ],
        )

        data = {
            "stats": {
                "challenges_solved": submission["challenges_solved"],
                "total_submissions": submission["total_submissions"],
                "success_rate": (
                    (
                        (
                            submission["total_submissions"]
                            / submission["challenges_solved"]
                        )
                        * 100
                    )
                    if submission["total_submissions"] > 0
                    else 0.0
                ),
            },
            "recent_submissions": SubmissionViewSerializer(
                submission[:3], many=True
            ).data,
            "continue_learning": ContinuLarningSerializer(continue_learning,many=True).data,
        }
