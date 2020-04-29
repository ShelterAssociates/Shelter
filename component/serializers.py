from rest_framework import serializers
from models import Metadata, Component
from master.models import Slum



class MetadataSerializer(serializers.ModelSerializer):

    count_of_component = serializers.SerializerMethodField('component_count')

    def component_count(self,obj):
        request_object = self.context['request']
        shelter_slum_id = request_object.query_params.get('slum_id')
        slum = Slum.objects.get(id=shelter_slum_id)
        total_component_count = slum.components.filter(metadata_id=obj)
        return total_component_count.count()

    class Meta:
        model = Metadata
        fields = ['id','name','level','blob','type','count_of_component']
