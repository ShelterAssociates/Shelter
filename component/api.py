from string import count

from rest_framework import viewsets

from .serializers import MetadataSerializer

from .models import Metadata
class MetadataViewSet(viewsets.ModelViewSet):
    queryset = Metadata.objects.filter(type = 'C')
    serializer_class = MetadataSerializer


