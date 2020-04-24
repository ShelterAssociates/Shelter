from rest_framework import serializers
from models import Metadata, Component
from master.models import Slum



class MetadataSerializer(serializers.ModelSerializer):

    components = serializers.SerializerMethodField('component_count')

    def component_count(self, slum_id):
        request_object = self.context['request']
        slum_id = request_object.query_params.get('slum_id')
        slum_data = Slum.objects.get(id=slum_id)
        print slum_data
        return slum_data.Component.objects.filter(Metadata.name).count()

    class Meta:
        model = Metadata
        fields = ['name','level','blob','type','components']
