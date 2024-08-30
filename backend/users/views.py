from django.contrib.auth import get_user_model
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import Subscription
from users.pagination import CustomPagination
from users.serializers import (
    CustomUserSerializer,
    CustomUserSubscriptionSerializer,
    UserAvatarSerializer,
)

CustomUser = get_user_model()


class UserAvatarUpdateView(generics.UpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserAvatarSerializer
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = self.request.user

        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        response_data = serializer.data
        response_data["avatar"] = (
            request.build_absolute_uri(user.avatar.url)
            if user.avatar
            else None
        )
        return Response(response_data)

    def delete(self, request):
        user = self.request.user

        if not user.avatar:
            return Response(
                {"detail": "Avatar not set"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.avatar.delete(save=True)
        return Response({"avatar": None}, status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_me_view(request):
    serializer = CustomUserSerializer(request.user)
    return Response(serializer.data)


class SubscriptionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def list(self, request):
        recipes_limit = request.query_params.get("recipes_limit", None)
        limit = request.query_params.get("limit", None)
        subscriptions = Subscription.objects.filter(
            user=request.user
        ).values_list("subscribed_to", flat=True)
        if limit:
            subscriptions = subscriptions[: int(limit)]
        paginator = self.pagination_class()
        paginated_subscriptions = paginator.paginate_queryset(
            subscriptions, request
        )
        serializer = CustomUserSubscriptionSerializer(
            CustomUser.objects.filter(id__in=paginated_subscriptions),
            many=True,
            context={"request": request, "recipes_limit": recipes_limit},
        )
        return paginator.get_paginated_response(serializer.data)

    def create(self, request, *args, **kwargs):
        user_id = self.kwargs.get("user_id")
        try:
            user_to_subscribe = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if request.user.id == user_to_subscribe.id:
            return Response(
                {"detail": "Cannot subscribe to yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription, created = Subscription.objects.get_or_create(
            user=request.user, subscribed_to=user_to_subscribe
        )

        if not created:
            return Response(
                {"detail": "Already subscribed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipes_limit = request.query_params.get("recipes_limit", None)

        serializer = CustomUserSubscriptionSerializer(
            user_to_subscribe,
            context={"request": request, "recipes_limit": recipes_limit},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        user_id = self.kwargs.get("user_id")
        try:
            user_to_unsubscribe = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            subscription = Subscription.objects.get(
                user=request.user, subscribed_to=user_to_unsubscribe
            )
            subscription.delete()
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "Not subscribed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Unsubscribed successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
