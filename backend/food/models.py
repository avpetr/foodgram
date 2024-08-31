import hashlib

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import JSONField, UniqueConstraint

from users.models import CustomUser

MAX_LENGTH = 150


class Tag(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH, verbose_name="Название тега"
    )
    slug = models.SlugField(unique=True, verbose_name="Слаг тега")

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH, verbose_name="Название ингредиента"
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH, verbose_name="Единица измерения"
    )

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH, verbose_name="Название рецепта"
    )
    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredient", verbose_name="Ингредиенты"
    )
    author = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, verbose_name="Автор"
    )
    text = models.TextField(verbose_name="Описание рецепта")
    image = models.ImageField(
        upload_to="recipes/images/",
        null=True,
        blank=True,
        verbose_name="Изображение рецепта",
    )
    tags = models.ManyToManyField(
        Tag, related_name="recipes", blank=True, verbose_name="Теги"
    )
    cooking_time = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Время приготовления (в минутах)",
    )
    short_link = models.CharField(
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Короткая ссылка",
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def get_short_link(self):
        return self.short_link

    def save(self, *args, **kwargs):
        if not self.short_link:
            self.short_link = self.generate_short_link()
        super().save(*args, **kwargs)

    def generate_short_link(self):
        hash_object = hashlib.md5(f"{self.id}{self.name}".encode())
        short_hash = hash_object.hexdigest()[:6]

        while Recipe.objects.filter(short_link=short_hash).exists():
            short_hash = hashlib.md5(short_hash.encode()).hexdigest()[:6]

        return short_hash

    def __str__(self):
        return f"Рецепт: {self.name} (Автор: {self.author.username})"


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, verbose_name="Рецепт"
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, verbose_name="Ингредиент"
    )
    amount = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Количество"
    )

    class Meta:
        verbose_name = "Ингредиент рецепта"
        verbose_name_plural = "Ингредиенты рецепта"
        constraints = [
            UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_recipe_ingredient",
            )
        ]

    def __str__(self):
        return (
            f"{self.ingredient.name} ({self.amount} "
            f"{self.ingredient.measurement_unit}"
            f"в {self.recipe.name}"
        )


class ShoppingList(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="shopping_lists",
        verbose_name="Пользователь",
    )
    recipe = models.ManyToManyField(
        Recipe, related_name="shopping_lists", verbose_name="Рецепты"
    )
    ingredients = JSONField(default=dict, verbose_name="Ингредиенты")

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"
        constraints = [
            models.UniqueConstraint(
                fields=["user"], name="unique_shopping_list_for_user"
            )
        ]

    def __str__(self):
        return f"Список покупок для {self.user.username}"


class FavoriteRecipe(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="favorite_recipe_set",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Рецепт",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_favorite_recipe"
            )
        ]
        verbose_name = "Избранный рецепт"
        verbose_name_plural = "Избранные рецепты"

    def __str__(self):
        return (
            f"Рецепт {self.recipe.name} добавлен"
            f" в избранное пользователем {self.user.username}"
        )
