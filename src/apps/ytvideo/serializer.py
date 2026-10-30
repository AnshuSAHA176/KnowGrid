from rest_framework import serializers
from .models import YtVideo, YtVideoChunks
from .transcipts_extract import YouTubeProcessor
from django.db import transaction
from .worker import process_youtube_video
from .services import check_slot, release_slot


class VideoCreateSerializer(serializers.ModelSerializer):
    url = serializers.URLField(required=True)

    class Meta:
        model = YtVideo
        fields = ["url", "youtube_id", "status", "created_at"]
        extra_kwargs = {
            "youtube_id": {"read_only": True},
            "status": {"read_only": True},
            "created_at": {"read_only": True},
        }

    def validate(self, attrs):
        if not attrs["url"]:
            raise serializers.ValidationError("You must Provide the url")
        user = self.context.get("request").user
        if not user:
            raise serializers.ValidationError("User is not provided")
        url_id = YouTubeProcessor().extract_video_id(url=attrs["url"])
        if not url_id:
            raise serializers.ValidationError("Please provide a valid url")
        attrs["url_id"] = url_id

        attrs["user"] = user
        return attrs

    def create(self, validated_data):
        aprroval = check_slot(validated_data["url_id"])
        if aprroval != "accepted":
            raise serializers.ValidationError(
                "No worker is free Please try after some time"
            )
        try:
            with transaction.atomic():

                yt_video = YtVideo.objects.create(
                    youtube_id=validated_data["url_id"], user=validated_data["user"]
                )
                transaction.on_commit(
                    lambda: process_youtube_video.delay(
                        video_id=yt_video.youtube_id, url=validated_data["url"]
                    )
                )
        except Exception:
            print(release_slot(job_id=validated_data["url_id"]))
            raise
        return yt_video


class VideoTitleSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source="user.email")

    class Meta:
        model = YtVideo
        fields = ["email", "youtube_id", "status"]


class VideoChunksSerializer(serializers.ModelSerializer):
    class Meta:
        model = YtVideoChunks
        fields = ["text", "start_time", "end_time"]
