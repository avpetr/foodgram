
from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from food.models import Recipe
from users.models import CustomUser, Subscription

CustomUser = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, subscribed_to=obj
            ).exists()
        return False


class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = CustomUser
        fields = ("email", "username", "first_name", "last_name", "password")

    def validate(self, attrs):
        if CustomUser.objects.filter(username=attrs.get("username")).exists():
            raise ValidationError("Username already exists.")
        return super().validate(attrs)

    def to_representation(self, instance):
        return {
            "email": instance.email,
            "id": instance.id,
            "username": instance.username,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
        }


class UserAvatarSerializer(CustomUserSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = CustomUser
        fields = ("avatar",)


class CustomUserSubscriptionSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
            "recipes",
            "recipes_count",
            "avatar",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, subscribed_to=obj
            ).exists()
        return False

    def get_recipes(self, obj):
        request = self.context.get("request")
        recipes_limit = self.context.get("recipes_limit")
        recipes = Recipe.objects.filter(author=obj)

        recipes_limit = self.context.get("recipes_limit")
        if recipes_limit is not None:
            recipes_limit = int(recipes_limit)
            recipes = recipes[:recipes_limit]
        return [
            {
                "id": recipe.id,
                "name": recipe.name,
                "image": (
                    request.build_absolute_uri(recipe.image.url)
                    if recipe.image
                    else None
                ),
                "cooking_time": recipe.cooking_time,
            }
            for recipe in recipes
        ]

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()
