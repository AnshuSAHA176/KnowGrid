from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User
from .serializer import RegisterSerializer, LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from apps.coding_challenges.models import Submission, CodingChallenge
from django.db.models import Count, Q, F, Exists, OuterRef, Subquery
from apps.coding_challenges.serializer import (
    SubmissionViewSerializer,
    ContinuLarningSerializer,
)


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

        stats_submission = Submission.objects.filter(user=request.user).aggregate(
            challenges_solved=Count(
                "id", filter=Q(status=Submission.StatusChoices.ACCEPTED), distinct=True
            ),
            total_submissions=Count("id"),
        )

        submission = (
            Submission.objects.select_related("challenge", "user")
            .filter(
                user=request.user,
            )
            .order_by("-created_at")
        )
        latest_submission = (
            Submission.objects.select_related("challenge")
            .filter(user=request.user, challenge_id=OuterRef("pk"))
            .order_by("-created_at", "-pk")
        )

        continue_learning = (
            CodingChallenge.objects.annotate(
                latest_submission_id=Subquery(latest_submission.values("id")[:1]),
                latest_submission_status=Subquery(
                    latest_submission.values("status")[:1]
                ),
            )
            .filter(
                latest_submission_status__in=[
                    Submission.StatusChoices.FAILED,
                    Submission.StatusChoices.PENDING,
                    Submission.StatusChoices.RUNNING,
                ]
            )
            .values(
                "id",
                "title",
                "latest_submission_status",
            )
        )

        data = {
            "stats": {
                "challenges_solved": stats_submission["challenges_solved"],
                "total_submissions": stats_submission["total_submissions"],
                "success_rate": (
                    (
                        (
                            stats_submission["total_submissions"]
                            / stats_submission["challenges_solved"]
                        )
                        * 100
                    )
                    if stats_submission["total_submissions"] > 0
                    else 0.0
                ),
            },
            "recent_submissions": SubmissionViewSerializer(
                submission[:3], many=True
            ).data,
            "continue_learning": continue_learning,
        }
        return Response(data)
