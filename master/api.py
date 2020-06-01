from django.http import request
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionDenied
from .serializers import CitySerializer
from .models import City

class CityViewset(viewsets.ModelViewSet):
    serializer_class = CitySerializer
    permission_classes = (IsAuthenticated,)
    queryset = City.objects.order_by('id')

    def get_queryset(self):
        user = self.request.user
        filter_queryset= {}
        if not user.is_superuser:
            filter_queryset['name__city_name__in'] = map(lambda x: x.split(':')[-1], user.groups.values_list('name', flat=True))
        queryset = City.objects.filter(**filter_queryset)
        if queryset.count() <=0:
            raise PermissionDenied("User do not have access to data")
        return queryset

