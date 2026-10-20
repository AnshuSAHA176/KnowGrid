from .views import ChallengesView,SubmissionView
from rest_framework.routers import DefaultRouter
from django.urls import path,include


router = DefaultRouter()
router.register(
    '',
    viewset=ChallengesView,
    basename = 'list_of_challenges'

   

)

urlpatterns =[
    path('videos/<youtube_id>/challenges/',include(router.urls),name='list_of_challenges'),
    path('challenges/<uuid:challenge_id>/submissions/',SubmissionView.as_view(),name='list_of_challenges'),
]