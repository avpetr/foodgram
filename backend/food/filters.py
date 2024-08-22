import django_filters

from food.models import Recipe


class RecipeFilter(django_filters.FilterSet):
    is_in_shopping_cart = django_filters.BooleanFilter(
        method="filter_is_in_shopping_cart"
    )
    is_favorited = django_filters.BooleanFilter(method="filter_is_favorited")

    class Meta:
        model = Recipe
        fields = [
            "author",
            "tags__slug",
            "is_in_shopping_cart",
            "is_favorited",
        ]

    def filter_is_favorited(self, queryset, name, value):
        print(f"Фильтр избранного вызван с value={value}")
        if not self.request.user.is_authenticated:
            return queryset.none()
        if value:
            return queryset.filter(favorited_by__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        print(f"Фильтр корзины вызван с value={value}")
        if not self.request.user.is_authenticated:
            return queryset.none()
        if value:
            return queryset.filter(shopping_lists__user=self.request.user)
        return queryset

    def __init__(self, *args, **kwargs):
        print("RecipeFilter инициализирован")
        super().__init__(*args, **kwargs)
