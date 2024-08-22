from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError

from food.models import (
    FavoriteRecipe,
    Ingredient,
    Recipe,
    RecipeIngredients,
    ShoppingList,
    ShoppingListItem,
    Tag,
)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name", "measurement_unit"]


class RecipeIngredientsSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer()

    class Meta:
        model = RecipeIngredients
        fields = ["ingredient", "amount"]


class ShoppingListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingListItem
        fields = ["name", "measurement_unit"]


class ShoppingListSerializer(serializers.ModelSerializer):
    items = ShoppingListItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = ["id", "user", "recipes", "items"]


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientsSerializer(
        many=True, read_only=True, source="recipeingredients_set"
    )
    author = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    image = Base64ImageField(required=False, allow_null=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        ]

    def get_author(self, obj):
        from users.serializers import CustomUserSerializer

        serializer = CustomUserSerializer(obj.author)
        return serializer.data

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return FavoriteRecipe.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return ShoppingList.objects.filter(
                user=request.user, recipes=obj
            ).exists()
        return False

    def validate(self, data):
        tags_data = self.context["request"].data.get("tags", [])
        ingredients_data = self.context["request"].data.get("ingredients", [])

        if not tags_data:
            raise ValidationError("At least one tag is required.")

        existing_tags = Tag.objects.filter(id__in=tags_data)
        if len(existing_tags) != len(tags_data):
            raise ValidationError("One or more tags do not exist.")

        if not ingredients_data:
            raise ValidationError("At least one ingredient is required.")

        ingredient_ids = [ingredient["id"] for ingredient in ingredients_data]
        existing_ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
        if len(existing_ingredients) != len(ingredient_ids):
            raise ValidationError("One or more ingredients do not exist.")

        seen_ingredient_ids = set()
        for ingredient_data in ingredients_data:
            if ingredient_data["amount"] < 1:
                raise ValidationError("Ingredient amount must be at least 1.")
            if ingredient_data["id"] in seen_ingredient_ids:
                raise ValidationError("Duplicate ingredients are not allowed.")
            seen_ingredient_ids.add(ingredient_data["id"])

        if not data.get("image"):
            raise ValidationError("An image is required.")

        return data

    def create(self, validated_data):
        tags_data = self.context["request"].data.get("tags", [])
        ingredients_data = self.context["request"].data.get("ingredients", [])

        recipe = Recipe.objects.create(**validated_data)

        recipe.tags.set(tags_data)

        for ingredient_data in ingredients_data:
            RecipeIngredients.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_data["id"],
                amount=ingredient_data["amount"],
            )

        return recipe

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user != instance.author:
            raise PermissionDenied(
                "Вы не можете редактировать этот рецепт, так как не являетесь его автором."
            )

        tags_data = self.context["request"].data.get("tags", [])
        ingredients_data = self.context["request"].data.get("ingredients", [])

        instance = super().update(instance, validated_data)

        instance.tags.set(tags_data)

        instance.recipeingredients_set.all().delete()
        for ingredient_data in ingredients_data:
            RecipeIngredients.objects.create(
                recipe=instance,
                ingredient_id=ingredient_data["id"],
                amount=ingredient_data["amount"],
            )

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation["ingredients"] = [
            {
                "id": item["ingredient"]["id"],
                "name": item["ingredient"]["name"],
                "measurement_unit": item["ingredient"]["measurement_unit"],
                "amount": float(item["amount"]),
            }
            for item in representation["ingredients"]
        ]

        return representation


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ["id", "name", "image", "cooking_time"]


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer()

    class Meta:
        model = FavoriteRecipe
        fields = ("id", "recipe")
