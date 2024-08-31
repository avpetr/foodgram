import base64
import csv
from random import choice, randint, sample

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from food.models import Ingredient, Recipe, RecipeIngredient, Tag


class Command(BaseCommand):
    help = (
        "Load data into the database from CSV "
        "and image files and create a superuser"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--ingredients", type=str, help="Path to the ingredients CSV file"
        )
        parser.add_argument(
            "--image", type=str, help="Path to the example image file"
        )

    def handle(self, *args, **options):
        ingredients_path = options["ingredients"]
        image_path = options["image"]

        def convert_image_to_base64(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")

        sample_image_base64 = convert_image_to_base64(image_path)

        User = get_user_model()
        superuser_email = "admin@example.com"
        superuser_password = "admin"
        superuser, created = User.objects.get_or_create(
            email=superuser_email,
            defaults={
                "username": "admin",
                "first_name": "Admin",
                "last_name": "User",
            },
        )
        if created:
            superuser.set_password(superuser_password)
            superuser.is_staff = True
            superuser.is_superuser = True
            superuser.save()
            self.stdout.write(
                self.style.SUCCESS("Superuser created successfully!")
            )
        else:
            self.stdout.write(self.style.WARNING("Superuser already exists."))

        ingredients = []
        with open(ingredients_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile, delimiter=",")
            for row in reader:
                if len(row) == 2:
                    name, measurement_unit = row
                    name = name.strip()
                    measurement_unit = measurement_unit.strip()
                    ingredient, created = Ingredient.objects.get_or_create(
                        name=name, measurement_unit=measurement_unit
                    )
                    ingredients.append(ingredient)

        users = []
        for i in range(5):
            email = f"user{i}@example.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": f"user{i}",
                    "first_name": f"First{i}",
                    "last_name": f"Last{i}",
                },
            )
            if created:
                user.set_password("password")
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user: {email}"))
            users.append(user)

        tag_names = ["Соленый", "Жареный", "Острый", "Кислый", "Сладкий"]
        tags = []
        for tag_name in tag_names:
            slug = tag_name.lower().replace(" ", "_")
            tag, created = Tag.objects.get_or_create(
                name=tag_name, defaults={"slug": slug}
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created tag: {tag_name}")
                )
            tags.append(tag)

        for i in range(10):
            author = choice(users)

            image_data = base64.b64decode(sample_image_base64)
            image = ContentFile(image_data, name=f"recipe_image_{i}.png")

            recipe = Recipe.objects.create(
                name=f"Recipe {i}",
                author=author,
                text=f"Delicious recipe {i}",
                cooking_time=randint(5, 60),
                image=image,
            )

            num_ingredients = randint(2, 5)
            selected_ingredients = sample(ingredients, num_ingredients)
            for ingredient in selected_ingredients:
                RecipeIngredient.objects.create(
                    recipe=recipe, ingredient=ingredient, amount=randint(1, 10)
                )

            num_tags = randint(1, 3)
            selected_tags = sample(tags, num_tags)
            recipe.tags.add(*selected_tags)

            self.stdout.write(
                self.style.SUCCESS(f"Created recipe: {recipe.name}")
            )

        self.stdout.write(
            self.style.SUCCESS("All recipes created successfully!")
        )
