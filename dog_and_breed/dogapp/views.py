from django.db.models import Avg, Count, IntegerField, OuterRef, Subquery
from django.db.models.manager import BaseManager
from rest_framework import viewsets

from dogapp.serializers import BreedSerializer, DogSerializer

from .models import Breed, Dog


class DogViewSet(viewsets.ModelViewSet):
    serializer_class = DogSerializer
    queryset = Dog.objects.all()

    def get_queryset(self) -> BaseManager[Dog]:
        match self.action:
            case "list":
                avg_age_subquery = (
                    Dog.objects.filter(breed=OuterRef("breed"))
                    .values("breed")
                    .annotate(avg_age=Avg("age"))
                    .values("avg_age")
                )

                return Dog.objects.select_related("breed").annotate(
                    avg_breed_age=Subquery(avg_age_subquery, output_field=IntegerField())
                )
            case "retrieve":
                return Dog.objects.select_related("breed").annotate(same_breed_count=Count("breed__dogs"))
            case _:
                return Dog.objects.all()


class BreedViewSet(viewsets.ModelViewSet):
    serializer_class = BreedSerializer
    queryset = Breed.objects.all()
