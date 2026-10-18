from django.urls import path
from .views import VideoView,RetriveView


urlpatterns = [
    path('',VideoView.as_view(),name='upload_video'),
    path('<str:youtube_id>/search/',RetriveView.as_view(),name='retrive_related_chunks'),
    
]