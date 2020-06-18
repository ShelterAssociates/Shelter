
from rest_framework import viewsets
from rest_framework import exceptions
from rest_framework.permissions import IsAuthenticated
from .serializers import MetadataSerializer
from .models import Metadata

class MetadataViewSet(viewsets.ModelViewSet):
    """
        Returns a list ['id','name','level','blob','type','component_data', 'count_of_component'] of metadata's with component details.

        input param - slum_id,
                 metadata_id,
                 fields(optional) : fields to be included,
                 omit(optional) : fields to be omitted
    """
    serializer_class = MetadataSerializer
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

