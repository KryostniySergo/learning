from rest_framework import serializers

from .models import Breed, Dog


class DogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dog
        fields = "__all__"

    avg_breed_age = serializers.IntegerField(read_only=True)
    same_breed_count = serializers.IntegerField(read_only=True)


class BreedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Breed
        fields = "__all__"

    dogs_count = serializers.IntegerField(read_only=True)
