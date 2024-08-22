import hashlib

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum

from users.models import CustomUser

MAX_LENGTH = 150


class Tag(models.Model):
    name = models.CharField(max_length=MAX_LENGTH, verbose_name="Тег рецепта")
    slug = models.SlugField(unique=True, verbose_name="Слаг тега")


class Ingredient(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH, verbose_name="Название ингредиента"
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH, verbose_name="Единица измерения"
    )


class Recipe(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH, verbose_name="Название рецепта"
    )
    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredients"
    )
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.TextField()
    image = models.ImageField(
        upload_to="recipes/images/",
        null=True,
        blank=True,
        verbose_name="Изображение рецепта",
    )
    tags = models.ManyToManyField(Tag, related_name="recipes", blank=True)
    cooking_time = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    def get_short_link(self):
        hash_object = hashlib.md5(f"{self.id}{self.name}".encode())
        short_hash = hash_object.hexdigest()[:3]  # Получаем короткий хеш
        return f"{settings.BASE_URL}/s/{short_hash}"


class RecipeIngredients(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=6, decimal_places=2)


class ShoppingList(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="shopping_lists"
    )
    recipes = models.ManyToManyField(Recipe, related_name="shopping_lists")

    def calculate_ingredients(self):
        # Очистить предыдущие элементы списка покупок
        self.items.all().delete()

        # Создать новые элементы списка покупок
        ingredients = Ingredient.objects.filter(
            recipeingredients__recipe__in=self.recipes.all()
        ).distinct()

        for ingredient in ingredients:
            total_amount = RecipeIngredients.objects.filter(
                recipe__in=self.recipes.all(), ingredient=ingredient
            ).aggregate(total_amount=Sum("amount"))["total_amount"]

            ShoppingListItem.objects.create(
                shopping_list=self, ingredient=ingredient, amount=total_amount
            )

    def __str__(self):
        return f"Shopping List for {self.user.username}"


class ShoppingListItem(models.Model):
    shopping_list = models.ForeignKey(
        ShoppingList, on_delete=models.CASCADE, related_name="items"
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.amount} of {self.ingredient.name} in Shopping List {self.shopping_list.id}"


class FavoriteRecipe(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="favorite_recipes_set",
    )  # Изменен related_name
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="favorited_by"
    )

    class Meta:
        unique_together = ("user", "recipe")
