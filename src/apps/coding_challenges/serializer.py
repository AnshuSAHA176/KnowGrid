from rest_framework import serializers

from .models import CodingChallenge, TestCase, Submission


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


from rest_framework import serializers

from .models import Submission


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = [
            "id",
            "challenge",
            "source_code",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_source_code(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Please enter your source code.")

        if len(value) > 50_000:
            raise serializers.ValidationError(
                "Source code cannot exceed 50,000 characters."
            )

        return value

    def validate(self, attrs):
        request = self.context["request"]
        attrs["user"] = request.user
        return attrs

    def create(self, validated_data):
        return Submission.objects.create(**validated_data)


class SubmissionViewSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email',read_only=True)
    title = serializers.CharField(source='challenge.title',read_only=True)
    class Meta:
        model = Submission
        fields = [
            'id',
            "email",
            "title",
            "status",
            'passed_tests',
            "created_at",
        ]


cla