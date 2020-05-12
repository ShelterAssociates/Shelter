from string import count

from rest_framework import viewsets

from .serializers import MetadataSerializer,ComponentSerializer

from .models import Metadata,Component
class MetadataViewSet(viewsets.ModelViewSet):
    queryset = Metadata.objects.filter(type = 'C')
    serializer_class = MetadataSerializer

class ComponentViewSet(viewsets.ModelViewSet):
    queryset = Component.objects.order_by('id')
    serializer_class = ComponentSerializer

