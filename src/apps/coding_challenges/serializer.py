
from rest_framework import serializers

from .models import CodingChallenge, TestCase


class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = [
            "id",
            "input_data",
            "expected_output",
            "is_hidden",
        ]


class CodingChallengTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodingChallenge
        fields = [
            "id",
            "title",
            "difficulty",
        ]


class CodingChallengSerializer(serializers.ModelSerializer):
    test_cases = TestCaseSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = CodingChallenge
        fields = [
            "id",
            "title",
            "description",
            "difficulty",
            "constraints",
            "starter_code",
            "test_cases",
        ]
