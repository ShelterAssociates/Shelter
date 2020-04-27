from rest_framework import serializers
from models import Metadata, Component
from master.models import Slum



class MetadataSerializer(serializers.ModelSerializer):

    components = serializers.SerializerMethodField('component_count')

    def component_count(self, shelter_slum_id):
        request_object = self.context['request']
        shelter_slum_id = request_object.query_params.get('slum_id')
        print shelter_slum_id
        slum_data = Slum.objects.get(id = shelter_slum_id)
        print slum_data
        count_of_components = slum_data.Component.filter(Metadata).count()
        return count_of_components
    class Meta:
        model = Metadata
        fields = ['name','level','blob','type','components']
