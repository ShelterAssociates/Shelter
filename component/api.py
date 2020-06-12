
from rest_framework import viewsets
from rest_framework import exceptions
from rest_framework.permissions import IsAuthenticated
from .serializers import MetadataSerializer,MetadataDetailsSerializer
from .models import Metadata

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
        slum_id = self.request.query_params.get('slum_id', None)
        if shelter_metadata_id == None or slum_id == None:
            raise exceptions.NotFound("Missing slum_id, metadata_id filters.")
        queryset = queryset.filter(id__in = shelter_metadata_id.split(','))
        return queryset

