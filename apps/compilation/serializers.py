from rest_framework import serializers


class ReviewChecklistItemSerializer(serializers.Serializer):
    clause_index = serializers.IntegerField()
    clause_text = serializers.CharField()
    citation_string = serializers.CharField(allow_blank=True)
    source_vector_ids = serializers.ListField(child=serializers.CharField())
    verification_verdict = serializers.CharField(allow_blank=True)
    verification_score = serializers.FloatField()
    is_null_field = serializers.BooleanField()
    is_approved = serializers.BooleanField()
    approved_at = serializers.DateTimeField(required=False, allow_null=True)
