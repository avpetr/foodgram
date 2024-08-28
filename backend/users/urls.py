from django.urls import include, path

from users.views import SubscriptionViewSet, UserAvatarUpdateView, user_me_view

subscription_list = SubscriptionViewSet.as_view({"get": "list"})
subscription_create = SubscriptionViewSet.as_view({"post": "create"})
subscription_destroy = SubscriptionViewSet.as_view({"delete": "destroy"})

urlpatterns = [
    path(
        "users/subscriptions/",
        subscription_list,
        name="user-subscriptions-list",
    ),
    path(
        "users/<int:user_id>/subscribe/",
        SubscriptionViewSet.as_view({"delete": "destroy", "post": "create"}),
        name="user-unsubscribe",
    ),
    path("users/me/", user_me_view, name="user-me"),
    path("", include("djoser.urls")),
    path("auth/", include("djoser.urls.authtoken")),
    path(
        "users/me/avatar/",
        UserAvatarUpdateView.as_view(),
        name="user-avatar-update",
    ),
]
