from rest_framework import serializers
from .models import facetemplateApp2, templateApp2, taskApp2, categoryToTemplateApp2


class taskApp2Serializer(serializers.ModelSerializer):
    class Meta:
        model = taskApp2
        fields = '__all__'


class templateApp2Serializer(serializers.ModelSerializer):
    class Meta:
        model = templateApp2
        fields = '__all__'


class facetemplateApp2Serializer(serializers.ModelSerializer):
    class Meta:
        model = facetemplateApp2
        fields = '__all__'

class categoryToTemplateApp2Serializer(serializers.ModelSerializer):
    class Meta:
        model = categoryToTemplateApp2
        fields = '__all__'
