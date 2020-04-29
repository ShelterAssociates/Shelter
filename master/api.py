from django.http import request
from rest_framework import viewsets

from .serializers import CitySerializer
from .models import City

class CityViewset(viewsets.ModelViewSet):
    serializer_class = CitySerializer
    queryset = City.objects.order_by('id')

