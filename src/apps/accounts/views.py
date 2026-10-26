from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User
from .serializer import RegisterSerializer, LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from apps.coding_challenges.models import Submission, CodingChallenge
from django.db.models import Count, Q, OuterRef, Subquery, Exists
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
                "challenge_id",
                filter=Q(status=Submission.StatusChoices.ACCEPTED),
                distinct=True,
                # challenge_id because all submission have its own uniuq id
                # that why we need to count the challenge id not the actual submission id
            ),
            accepted_submission=Count(
                "id", filter=Q(status=Submission.StatusChoices.ACCEPTED)
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

        # Imagine KnowGrid has many users and coding challenges. You need to find each user's latest submission for every challenge,
        # then identify challenges where the latest submission failed but the user has never passed that challenge.

        latest_user_submission = Submission.objects.filter(
            user=request.user, challenge_id=OuterRef("pk")
        ).order_by("-created_at", "-pk")

        accepted_submissions=Submission.objects.filter(
                user=request.user,
                challenge_id=OuterRef("pk"),
                status=Submission.StatusChoices.ACCEPTED,
            )
        
        fail_submissions = CodingChallenge.objects.annotate(
            submission_id=Subquery(latest_user_submission.values("id")[:1]),
            latest_submission_status=Subquery(
                latest_user_submission.values("status")[:1]
            ),
            latest_submission_timestamp=Subquery(latest_user_submission.values('created_at')[:1]),
            
            has_accept=Exists(accepted_submissions)
        ).filter(
            latest_submission_status=Submission.StatusChoices.FAILED,
            has_accept=False
        ).order_by('-latest_submission_timestamp').values('id','latest_submission_status','submission_id')

        data = {
            "stats": {
                "challenges_solved": stats_submission["challenges_solved"],
                "total_submissions": stats_submission["total_submissions"],
                "success_rate": (
                    (
                        (
                            stats_submission["accepted_submission"]
                            / stats_submission["total_submissions"]
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
            "continue_learning": list(continue_learning),
        }
        return Response(data)
