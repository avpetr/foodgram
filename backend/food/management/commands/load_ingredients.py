from django.core.management.base import BaseCommand
from food.models import Ingredient

class Command(BaseCommand):
    help = 'Загрузка ингредиентов из файла'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Путь до csv файла ингредиентов')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']

        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:
                    name, measurement_unit = line.rsplit(',', 1)
                    Ingredient.objects.get_or_create(name=name.strip(), measurement_unit=measurement_unit.strip())

        self.stdout.write(self.style.SUCCESS('Ингредиенты успешно загружены'))