import csv
from io import StringIO
import os

from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from rest_framework import status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView, View

from food.models import FavoriteRecipe, Ingredient, Recipe, ShoppingList, Tag
from food.pagination import CustomPageNumberPagination
from food.permissions import IsAuthorOrReadOnly
from food.serializers import (
    IngredientSerializer,
    RecipeIngredient,
    RecipeSerializer,
    RecipeShortSerializer,
    TagSerializer,
)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None
    http_method_names = ["get"]


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None

    filter_backends = [SearchFilter]
    search_fields = ["^name"]

    http_method_names = ["get"]

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            name = name.lower()
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()

        author = self.request.query_params.get("author")
        if author:
            queryset = queryset.filter(author=author)

        tags = self.request.query_params.getlist("tags")
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        is_favorited = self.request.query_params.get("is_favorited")
        if is_favorited == "1" and self.request.user.is_authenticated:
            queryset = queryset.filter(favorited_by__user=self.request.user)

        is_in_shopping_cart = self.request.query_params.get(
            "is_in_shopping_cart"
        )
        if is_in_shopping_cart == "1" and self.request.user.is_authenticated:
            queryset = queryset.filter(shopping_lists__user=self.request.user)

        return queryset

    def perform_create(self, serializer):
        instance = serializer.save(author=self.request.user)
        return instance


class RedirectShortLinkView(View):
    def get(self, request, short_hash):
        recipe = get_object_or_404(Recipe, short_link=short_hash)
        return redirect(f"{settings.BASE_URL}recipes/{recipe.id}/")


class GetShortLinkView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        short_link = recipe.get_short_link()
        full_short_link = f"{settings.BASE_URL}api/s/{short_link}/"
        return Response({"short-link": full_short_link}, status=200)


class ShoppingCartMixin:
    def get_recipe_and_shopping_list(self, user, recipe_id, model):
        recipe = get_object_or_404(Recipe, id=recipe_id)

        if model == FavoriteRecipe:
            favorite_recipe, created = model.objects.get_or_create(
                user=user, recipe=recipe
            )
            return recipe, favorite_recipe
        else:
            shopping_list, created = model.objects.get_or_create(user=user)
            return recipe, shopping_list

    def get_recipe(self, recipe_id):
        return get_object_or_404(Recipe, id=recipe_id)

    def add_item(self, request, model, name, *args, **kwargs):
        recipe = self.get_recipe(self.kwargs.get("recipe_id"))

        if model.objects.filter(user=request.user, recipe=recipe).exists():
            return Response(
                {"detail": f"Recipe already in {name}."}, status=400
            )

        if model == FavoriteRecipe:
            model.objects.create(user=request.user, recipe=recipe)
        else:
            shopping_list, created = model.objects.get_or_create(
                user=request.user
            )
            shopping_list.recipe.add(recipe)

        serializer = RecipeShortSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ManageShoppingCart(APIView, ShoppingCartMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request, recipe_id, *args, **kwargs):
        return self.add_item(
            request, ShoppingList, "shopping cart", *args, **kwargs
        )

    def delete(self, request, recipe_id):
        recipe, shopping_list = self.get_recipe_and_shopping_list(
            request.user, recipe_id, ShoppingList
        )

        if not shopping_list.recipe.filter(id=recipe.id).exists():
            return Response(
                {"detail": "Recipe not in shopping cart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shopping_list.recipe.remove(recipe)
        return Response(
            {"detail": "Recipe removed from shopping cart."}, status=204
        )


class DownloadShoppingCart(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            shopping_list = ShoppingList.objects.get(user=user)
        except ShoppingList.DoesNotExist:
            return Response("No shopping list found.", status=404)

        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__in=shopping_list.recipe.all()
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
        )

        # Определяем максимальные длины для выравнивания столбцов
        max_len_name = max(len("Ингредиент"), max(len(item["ingredient__name"]) for item in ingredients))
        max_len_unit = max(len("Единица измерения"), max(len(item["ingredient__measurement_unit"]) for item in ingredients))
        max_len_amount = max(len("Количество"), max(len(f"{item['total_amount']:.2f}") for item in ingredients))

        # Создаем временный файл
        file_path = os.path.join(os.path.dirname(__file__), 'shopping_list.txt')
        
        with open(file_path, 'w', encoding='utf-8') as file:
            # Добавляем заголовок
            file.write(f"Список покупок для пользователя: {user.email}\n\n")
            
            # Заголовок таблицы
            file.write(f"{'Ингредиент'.ljust(max_len_name)} | {'Единица измерения'.ljust(max_len_unit)} | {'Количество'.rjust(max_len_amount)}\n")
            file.write("-" * (max_len_name + max_len_unit + max_len_amount + 6) + "\n")
            
            # Строки с ингредиентами
            for item in ingredients:
                name = item["ingredient__name"].ljust(max_len_name)
                measurement_unit = item["ingredient__measurement_unit"].ljust(max_len_unit)
                total_amount = item['total_amount']
                
                # Проверка, целое ли число
                if total_amount == total_amount.to_integral_value():
                    total_amount = f"{int(total_amount)}"
                else:
                    total_amount = f"{total_amount:.2f}"

                total_amount = total_amount.rjust(max_len_amount)
                file.write(f"{name} | {measurement_unit} | {total_amount}\n")

        # Открываем файл для чтения и отправки пользователю
        with open(file_path, 'r', encoding='utf-8') as file:
            response = HttpResponse(file.read(), content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="shopping_list.txt"'

        # Удаляем временный файл
        os.remove(file_path)

        return response


class FavoriteRecipeViewSet(viewsets.ViewSet, ShoppingCartMixin):
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        return self.add_item(
            request, FavoriteRecipe, "favorites", *args, **kwargs
        )

    def destroy(self, request, recipe_id):
        recipe, favorite_recipe = self.get_recipe_and_shopping_list(
            request.user, recipe_id, FavoriteRecipe
        )

        if not favorite_recipe:
            return Response(
                {"detail": "Recipe not in favorites."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        favorite_recipe.delete()
        return Response(
            {"detail": "Recipe removed from favorites."},
            status=status.HTTP_204_NO_CONTENT,
        )
