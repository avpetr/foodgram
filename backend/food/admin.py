from django.contrib import admin

from .models import (FavoriteRecipe, Ingredient, Recipe, RecipeIngredient,
                     ShoppingList, Tag)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "measurement_unit"]
    search_fields = ["name"]


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "author", "get_favorites_count"]
    search_fields = ["name", "author__username"]
    list_filter = ["tags"]
    inlines = [RecipeIngredientInline]

    def get_favorites_count(self, obj):
        return obj.favorited_by.count()

    get_favorites_count.short_description = "Количество добавлений в избранное"


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ["id", "user"]
    search_fields = ["user__username"]
    filter_horizontal = ["recipes"]


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ["user", "recipe"]
    list_filter = ["user", "recipe"]
    search_fields = ["user__username", "recipe__name"]
