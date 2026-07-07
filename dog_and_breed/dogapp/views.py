from rest_framework import viewsets

from dogapp.serializers import BreedSerializer, DogSerializer

from .models import Breed, Dog


class DogViewSet(viewsets.ModelViewSet):
    serializer_class = DogSerializer
    queryset = Dog.objects.all()


class BreedViewSet(viewsets.ModelViewSet):
    serializer_class = BreedSerializer
    queryset = Breed.objects.all()
