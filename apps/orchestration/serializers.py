from rest_framework import serializers


class SubmitQuerySerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True)
    raw_query = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)
    template_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class QuerySessionSerializer(serializers.Serializer):
    query_id = serializers.UUIDField()
    session_id = serializers.UUIDField()
    raw_query = serializers.CharField()
    intent = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    result_payload = serializers.JSONField(required=False, allow_null=True)
    verification_report = serializers.JSONField(required=False, allow_null=True)
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
