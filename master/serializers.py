from rest_framework import serializers
from models import City, AdministrativeWard, Slum, ElectoralWard, CityReference


class SlumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slum
        fields = ['name', 'id']


class AdminWard(serializers.ModelSerializer):
    slum_name = serializers.SerializerMethodField('get_slum_names')

    def get_slum_names(self, obj):
        slum = Slum.objects.filter(electoral_ward__administrative_ward=obj)
        return SlumSerializer(slum, many=True).data

    class Meta:
        model = AdministrativeWard
        fields = ['name', 'id', 'slum_name']


class CitySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField('get_city_names')
    admin_ward = AdminWard(many=True)

    def get_city_names(self, obj):
        return obj.name.city_name

    class Meta:
        model = City
        fields = ['id', 'name', 'admin_ward']
