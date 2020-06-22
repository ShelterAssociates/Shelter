from rest_framework import serializers
from drf_dynamic_fields import DynamicFieldsMixin
from .models import Metadata, Component
from master.models import Slum

class MetadataSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    component_data = serializers.SerializerMethodField('get_component_details')
    count_of_component = serializers.SerializerMethodField('component_count')

    def component_count(self,obj):
        request_object = self.context['request']
        shelter_slum_id = request_object.query_params.get('slum_id')
        slum = Slum.objects.get(id=shelter_slum_id)
        total_component_count = slum.components.filter(metadata_id=obj)
        return total_component_count.count()

    def get_component_details(self,param):
        request_object = self.context['request']
        shelter_slum_id = request_object.query_params.get('slum_id')
        shelter_metadata_id = request_object.query_params.get('metadata_id')
        slum = Slum.objects.get(id=shelter_slum_id)
        comp = slum.components.filter(metadata=param)
        temp = ComponentSerializer(comp, many=True).data
        return temp

    class Meta:
        model = Metadata
        fields = ['id','name','level','blob','type','component_data', 'count_of_component']

class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = ['id','shape','housenumber']