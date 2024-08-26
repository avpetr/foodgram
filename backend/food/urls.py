from django.urls import include, path
from rest_framework.routers import DefaultRouter

from food.views import (DownloadShoppingCart, FavoriteRecipeViewSet,
                    IngredientViewSet, ManageShoppingCart,
                    RecipeViewSet, TagViewSet, RedirectShortLinkView, GetShortLinkView)

router = DefaultRouter()
router.register(r"tags", TagViewSet)
router.register(r"ingredients", IngredientViewSet)
router.register(r"recipes", RecipeViewSet)

urlpatterns = [
    path('s/<str:short_hash>/', RedirectShortLinkView.as_view(), name='short_link'),
    
    path(
        "recipes/<int:recipe_id>/favorite/",
        FavoriteRecipeViewSet.as_view(
            {
                "post": "create",
                "delete": "destroy",
            }
        ),
        name="recipe-favorite",
    ),
    path('recipes/<int:pk>/', RecipeViewSet.as_view({'get': 'retrieve'}), name='recipe-detail'),
    path(
        "recipes/<int:pk>/get-link/",
        GetShortLinkView.as_view(),
        name="recipe-get-link",
    ),
    
    path(
        "recipes/<int:recipe_id>/shopping_cart/",
        ManageShoppingCart.as_view(),
        name="manage-shopping-cart",
    ),
    path(
        "recipes/download_shopping_cart/",
        DownloadShoppingCart.as_view(),
        name="download-shopping-cart",
    ),
    path("", include(router.urls)),
    
]
