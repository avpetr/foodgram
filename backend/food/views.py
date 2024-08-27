import csv
from io import StringIO

from django.conf import settings
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from food.models import FavoriteRecipe, Ingredient, Recipe, ShoppingList, Tag
from food.permissions import IsAuthorOrReadOnly
from food.serializers import (
    IngredientSerializer,
    RecipeIngredient,
    RecipeSerializer,
    RecipeShortSerializer,
    TagSerializer,
)
from rest_framework import status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView, View


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
    def get_recipe_and_shopping_list(self, user, recipe_id):
        recipe = get_object_or_404(Recipe, id=recipe_id)
        shopping_list, created = ShoppingList.objects.get_or_create(user=user)
        return recipe, shopping_list


class ManageShoppingCart(APIView, ShoppingCartMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request, recipe_id):
        recipe, shopping_list = self.get_recipe_and_shopping_list(
            request.user, recipe_id
        )

        if recipe in shopping_list.recipes.all():
            return Response(
                {"detail": "Recipe already in shopping cart."}, status=400
            )

        shopping_list.recipes.add(recipe)
        shopping_list.calculate_ingredients()
        serializer = RecipeShortSerializer(recipe)
        return Response(serializer.data, status=201)

    def delete(self, request, recipe_id):
        recipe, shopping_list = self.get_recipe_and_shopping_list(
            request.user, recipe_id
        )

        if recipe not in shopping_list.recipes.all():
            return Response(
                {"detail": "Recipe not in shopping cart."}, status=400
            )

        shopping_list.recipes.remove(recipe)
        shopping_list.calculate_ingredients()

        return Response(
            {"detail": "Recipe removed from shopping cart."}, status=204
        )


class DownloadShoppingCart(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Попытка найти список покупок пользователя
        try:
            shopping_list = ShoppingList.objects.get(user=user)
        except ShoppingList.DoesNotExist:
            return Response("No shopping list found.", status=404)

        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__in=shopping_list.recipes.all()
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
        )

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Ingredient", "Measurement Unit", "Amount"])

        for item in ingredients:
            writer.writerow(
                [
                    item["ingredient__name"],
                    item["ingredient__measurement_unit"],
                    item["total_amount"],
                ]
            )

        # Сохранение данных и подготовка ответа
        output.seek(0)
        response = Response(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="shopping_list.csv"'
        )

        return response


class FavoriteRecipeViewSet(viewsets.ViewSet, ShoppingCartMixin):
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        recipe, _ = self.get_recipe_and_shopping_list(
            request.user, self.kwargs.get("recipe_id")
        )

        if FavoriteRecipe.objects.filter(
            user=request.user, recipe=recipe
        ).exists():
            return Response(
                {"detail": "Recipe already in favorites."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        FavoriteRecipe.objects.create(user=request.user, recipe=recipe)

        serializer = RecipeShortSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        recipe, _ = self.get_recipe_and_shopping_list(
            request.user, self.kwargs.get("recipe_id")
        )

        favorite = FavoriteRecipe.objects.filter(
            user=request.user, recipe=recipe
        ).first()
        if favorite:
            favorite.delete()
            return Response(
                {"detail": "Recipe removed from favorites."},
                status=status.HTTP_204_NO_CONTENT,
            )

        return Response(
            {"detail": "Recipe not in favorites."},
            status=status.HTTP_400_BAD_REQUEST,
        )
