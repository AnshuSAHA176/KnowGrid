from rest_framework import serializers
from .models import CodingChallenge, Submission, TestCase


class CodingChallengTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodingChallenge
        fields = [
            "id",
            "video",
            "title",
        ]


class CodingChallengSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodingChallenge
        fields = [
            "id",
            "video",
            "title",
            "description",
            "difficulty",
            "starter_code",
            "input_data",
        ]
