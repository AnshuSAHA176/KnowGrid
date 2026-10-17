from rest_framework import serializers
from .models import YtVideo
from .transcipts_extract import YouTubeProcessor
from django.db import transaction
from .worker import process_youtube_video


class VideoCreateSerializer(serializers.ModelSerializer):
    url = serializers.URLField(required=True)

    class Meta:
        model = YtVideo
        fields = ["youtube_id", "status", "created_at"]
        extra_kwargs = {
            {
                "youtube_id": {"read_only": True},
                "status": {"read_only": True},
                "created_at": {"read_only": True},
            }
        }

    def validate(self, attrs):
        if not attrs["url"]:
            raise serializers.ValidationError("You must Provide the url")
        user = self.context.get("request").user
        if not user:
            raise serializers.ValidationError("User is not provided")
        attrs["user"] = user
        return attrs

    def create(self, validated_data):

        with transaction.atomic():
            url_id = YouTubeProcessor().extract_video_id(url=validated_data["url"])
            yt_video = YtVideo.objects.create(
                youtube_id=url_id, user=validated_data["user"]
            )
            transaction.on_commit(
                lambda: process_youtube_video.delay(
                    video_id=yt_video.youtube_id, url=validated_data["url"]
                )
            )
        return yt_video


class VideoTitleSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source = 'user.email')
    class Meta:
        model = YtVideo
        fields =[
            ''
        ]