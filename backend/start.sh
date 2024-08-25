python manage.py flush --no-input
python manage.py makemigrations
python manage.py migrate
echo "from django.contrib.auth import get_user_model;\
 User = get_user_model();\
 User.objects.create_superuser('admin', 'admin');\
 from food.models import Tag, Ingredient;\
 tag1 = Tag(name='Соленый', slug='solenij');\
 tag2 = Tag(name='Жареный', slug='zhareniy');\
 tag3 = Tag(name='Острый', slug='ostrij');\
 tag1.save();\
 tag2.save();\
 tag3.save(); "| python manage.py shell
 python manage.py load_ingredients ../data/ingredients.csv
python manage.py runserver
