
from rest_framework import viewsets

from component import models
from .serializers import MetadataSerializer,MetadataDetailsSerializer
from .models import Metadata
from requests import request
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionDenied

class MetadataViewSet(viewsets.ModelViewSet):
    queryset = Metadata.objects.filter(type = 'C')
    permission_classes = (IsAuthenticated,)
    serializer_class = MetadataSerializer

class ComponentViewSet(viewsets.ModelViewSet):
    serializer_class = MetadataDetailsSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Metadata.objects.filter(type = 'C')
    
    def get_queryset(self):
        queryset = Metadata.objects.filter(type = 'C')
        shelter_metadata_id = self.request.query_params.get('metadata_id', None)
        queryset = queryset.filter(id__in = shelter_metadata_id.split(','))
        return queryset

