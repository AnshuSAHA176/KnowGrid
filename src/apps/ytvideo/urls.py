from django.urls import path
from .views import VideoView


urlpatterns = [
    path('',VideoView.as_view(),name='upload_video'),
    
]