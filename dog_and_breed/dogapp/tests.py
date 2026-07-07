"""Тесты для приложения dogapp (модели и ViewSet'ы)."""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Breed, Dog

# ========================
# MODEL TESTS
# ========================


class BreedModelTest(TestCase):
    """Тесты для модели Breed."""

    def setUp(self):
        """Создаёт тестовую породу перед каждым тестом."""
        self.breed = Breed.objects.create(
            name="Labrador Retriever",
            size=Breed.Sizes.LARGE,
            friendliness=5,
            trainability=4,
            shedding_amount=3,
            exercise_needs=5,
        )

    def test_breed_creation(self):
        """Проверяет корректное создание объекта Breed и валидацию полей."""
        self.assertEqual(self.breed.name, "Labrador Retriever")
        self.assertEqual(self.breed.size, "Large")
        self.assertEqual(self.breed.friendliness, 5)
        self.assertTrue(1 <= self.breed.friendliness <= 5)

    def test_breed_str(self):
        """Проверяет корректную работу метода __str__ модели Breed."""
        self.assertEqual(str(self.breed), "Labrador Retriever")


class DogModelTest(TestCase):
    """Тесты для модели Dog."""

    def setUp(self):
        """Создаёт тестовую породу и собаку перед каждым тестом."""
        self.breed = Breed.objects.create(
            name="Golden Retriever",
            size=Breed.Sizes.LARGE,
            friendliness=5,
            trainability=4,
            shedding_amount=3,
            exercise_needs=4,
        )
        self.dog = Dog.objects.create(
            name="Buddy",
            age=3,
            breed=self.breed,
            gender="Male",
            color="Golden",
            favorite_food="Chicken",
            favorite_toy="Ball",
        )

    def test_dog_creation(self):
        """Проверяет корректное создание объекта Dog."""
        self.assertEqual(self.dog.name, "Buddy")
        self.assertEqual(self.dog.age, 3)
        self.assertEqual(self.dog.breed, self.breed)
        self.assertEqual(self.dog.gender, "Male")

    def test_dog_str(self):
        """Проверяет корректную работу метода __str__ модели Dog."""
        self.assertEqual(str(self.dog), "Buddy")


# ========================
# API TESTS
# ========================


class BreedViewSetTest(APITestCase):
    """Тесты для BreedViewSet."""

    def setUp(self):
        """Создаёт тестовые данные пород и собак."""
        self.breed1 = Breed.objects.create(
            name="Poodle", size=Breed.Sizes.SMALL, friendliness=4, trainability=5, shedding_amount=1, exercise_needs=3
        )
        self.breed2 = Breed.objects.create(
            name="Bulldog",
            size=Breed.Sizes.MEDIUM,
            friendliness=3,
            trainability=2,
            shedding_amount=2,
            exercise_needs=2,
        )
        Dog.objects.create(
            name="Max",
            age=2,
            breed=self.breed1,
            gender="Male",
            color="White",
            favorite_food="Meat",
            favorite_toy="Bone",
        )
        Dog.objects.create(
            name="Luna",
            age=4,
            breed=self.breed1,
            gender="Female",
            color="Black",
            favorite_food="Fish",
            favorite_toy="Toy",
        )

    def test_breed_list(self):
        """Проверяет GET /breeds/ — список пород с аннотацией dogs_count."""
        url = reverse("breed-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        poodle = next(b for b in response.data if b["name"] == "Poodle")
        self.assertEqual(poodle["dogs_count"], 2)

    def test_breed_retrieve(self):
        """Проверяет GET /breeds/{id}/ — детальную информацию о породе."""
        url = reverse("breed-detail", args=[self.breed1.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Poodle")
        self.assertEqual(response.data["dogs_count"], 2)


class DogViewSetTest(APITestCase):
    """Тесты для DogViewSet."""

    def setUp(self):
        """Создаёт тестовые данные пород и собак для проверки аннотаций."""
        self.breed1 = Breed.objects.create(
            name="Beagle", size=Breed.Sizes.SMALL, friendliness=5, trainability=4, shedding_amount=3, exercise_needs=4
        )
        self.breed2 = Breed.objects.create(
            name="Husky", size=Breed.Sizes.LARGE, friendliness=4, trainability=3, shedding_amount=4, exercise_needs=5
        )

        self.dog1 = Dog.objects.create(
            name="Charlie",
            age=2,
            breed=self.breed1,
            gender="Male",
            color="Brown",
            favorite_food="Beef",
            favorite_toy="Stick",
        )
        self.dog2 = Dog.objects.create(
            name="Bella",
            age=5,
            breed=self.breed1,
            gender="Female",
            color="White",
            favorite_food="Chicken",
            favorite_toy="Ball",
        )
        self.dog3 = Dog.objects.create(
            name="Rocky",
            age=3,
            breed=self.breed2,
            gender="Male",
            color="Gray",
            favorite_food="Salmon",
            favorite_toy="Frisbee",
        )

    def test_dog_list_with_avg_age(self):
        """Проверяет GET /dogs/ — список собак с аннотацией avg_breed_age."""
        url = reverse("dog-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем аннотацию среднего возраста по породе
        beagle_dogs = [d for d in response.data if d.get("breed") == self.breed1.pk]
        for dog in beagle_dogs:
            self.assertIn("avg_breed_age", dog)
            self.assertEqual(dog["avg_breed_age"], 3)  # (2 + 5) / 2 = 3.5 → 3

    def test_dog_retrieve_with_same_breed_count(self):
        """Проверяет GET /dogs/{id}/ — детальную карточку собаки с same_breed_count."""
        url = reverse("dog-detail", args=[self.dog1.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Charlie")
        self.assertEqual(response.data.get("same_breed_count"), 2)

    def test_dog_create(self):
        """Проверяет POST /dogs/ — создание новой собаки."""
        url = reverse("dog-list")
        data = {
            "name": "NewDog",
            "age": 1,
            "breed": self.breed1.pk,
            "gender": "Female",
            "color": "Black",
            "favorite_food": "Rice",
            "favorite_toy": "Rope",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Dog.objects.count(), 4)
        self.assertEqual(response.data["name"], "NewDog")
