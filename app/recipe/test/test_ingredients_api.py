from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientsApiTests(TestCase):
    """Test the publicly available ingredients api"""
    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required"""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test the private ingredients api"""
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@test.de',
            'Test123'
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_ingredients_list(self):
        """Test retrieving alist of ingredients"""
        Ingredient.objects.create(user=self.user, name='Meat')
        Ingredient.objects.create(user=self.user, name='Salt')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test hat onyl ingredients for the authenticated user are returned"""
        user2 = get_user_model().objects.create_user(
            'asd@test.de'
            'Test123'
        )

        Ingredient.objects.create(user=user2, name='Pepper')
        ingredient = Ingredient.objects.create(user=self.user, name='Chicken')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)

    def test_create_ingredient_successful(self):
        """Test that a ingredient is created successfull"""
        payload = {'name': 'salt'}
        self.client.post(INGREDIENTS_URL, payload)

        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()

        self.assertTrue(exists)

    def test_create_ingredient_invalid(self):
        """Test for creating an invalid ingredient"""
        payload = {'name': ''}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_ingredients_assigned_to_recipes(self):
        """Test filter for assigned ingredients"""
        i1 = Ingredient.objects.create(user=self.user)
        i2 = Ingredient.objects.create(user=self.user, name='turkey')

        recipe = Recipe.objects.create(
            title='Awesome recipe',
            time_minutes=10,
            price=10.00,
            user=self.user
        )

        recipe.ingredients.add(i1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(i1)
        s2 = IngredientSerializer(i2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_retrieve_ingredients_assigned_unique(self):
        """Test filtering ingredients by assigned returns unique items"""
        ingredient = Ingredient.objects.create(user=self.user)
        Ingredient.objects.create(user=self.user, name='cheese')

        r1 = Recipe.objects.create(
            title='Awesome recipe',
            time_minutes=10,
            price=10.00,
            user=self.user
        )
        r1.ingredients.add(ingredient)

        r2 = Recipe.objects.create(
            title='Awesome recipe 2',
            time_minutes=10,
            price=10.00,
            user=self.user
        )
        r2.ingredients.add(ingredient)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
