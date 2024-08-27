import hashlib

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
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
        Ingredient, through="RecipeIngredients", verbose_name="Ингредиенты"
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


class RecipeIngredients(models.Model):
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

    def __str__(self):
        return (f"{self.ingredient.name} ({self.amount} "
                f"{self.ingredient.measurement_unit}"
                f"в {self.recipe.name}")


class ShoppingList(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="shopping_lists",
        verbose_name="Пользователь",
    )
    recipes = models.ManyToManyField(
        Recipe, related_name="shopping_lists", verbose_name="Рецепты"
    )

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"

    def calculate_ingredients(self):
        self.items.all().delete()

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
        return f"Список покупок для {self.user.username}"


class ShoppingListItem(models.Model):
    shopping_list = models.ForeignKey(
        ShoppingList,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Список покупок",
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, verbose_name="Ингредиент"
    )
    amount = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Количество"
    )

    class Meta:
        verbose_name = "Элемент списка покупок"
        verbose_name_plural = "Элементы списка покупок"

    def __str__(self):
        return (f"{self.amount} {self.ingredient.measurement_unit} "
                f"{self.ingredient.name}"
                f" в списке покупок {self.shopping_list.id}")


class FavoriteRecipe(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="favorite_recipes_set",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Рецепт",
    )

    class Meta:
        unique_together = ("user", "recipe")
        verbose_name = "Избранный рецепт"
        verbose_name_plural = "Избранные рецепты"

    def __str__(self):
        return (f"Рецепт {self.recipe.name} добавлен"
                f" в избранное пользователем {self.user.username}")
