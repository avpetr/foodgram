from django.contrib import admin
from food.models import (FavoriteRecipe, Ingredient, Recipe, RecipeIngredients,
                         ShoppingList, ShoppingListItem, Tag)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "measurement_unit"]
    search_fields = ["name"]

class RecipeIngredientsInline(admin.TabularInline):
    model = RecipeIngredients
    extra = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "author", "favorite_count"]  # Добавляем метод `favorite_count`
    search_fields = ["name", "author__username"]
    list_filter = ["tags"]  # Фильтрация по тегам
    inlines = [RecipeIngredientsInline]

    def favorite_count(self, obj):
        return obj.favorite_set.count()  # Предполагается, что у Recipe есть связь с FavoriteRecipe
    favorite_count.short_description = "Favorite Count"

@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
    ]
    search_fields = ["user__username"]
    filter_horizontal = ["recipes"]

class ShoppingListItemInline(admin.TabularInline):
    model = ShoppingListItem
    extra = 1

@admin.register(ShoppingListItem)
class ShoppingListItemAdmin(admin.ModelAdmin):
    list_display = ["id", "shopping_list", "ingredient", "amount"]
    search_fields = ["shopping_list__user__username", "ingredient__name"]

@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    list_filter = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")
