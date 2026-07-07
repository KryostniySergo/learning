from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# Create your models here.
class Breed(models.Model):
    class Sizes(models.TextChoices):
        TINY = "Tiny", "Tiny"
        SMALL = "Small", "Small"
        MEDIUM = "Medium", "Medium"
        LARGE = "Large", "Large"

    name: str = models.CharField()
    size: str = models.CharField(choices=Sizes.choices)
    friendliness: int = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    trainability: int = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    shedding_amount: int = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    exercise_needs: int = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    def __str__(self) -> str:
        """__str__ Возвращает имя Породы

        Returns:
            str: Имя породы
        """
        return self.name


class Dog(models.Model):
    name: str = models.CharField()
    age: int = models.IntegerField()
    breed = models.ForeignKey(Breed, on_delete=models.CASCADE, related_name="dogs")
    gender: str = models.CharField()
    color: str = models.CharField()
    favorite_food: str = models.CharField()
    favorite_toy: str = models.CharField()

    def __str__(self) -> str:
        """__str__ Возвращает имя Собаки

        Returns:
            str: Имя собаки
        """
        return self.name
