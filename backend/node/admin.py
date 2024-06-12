from django.contrib import admin
from .models import taskApp2, templateApp2, facetemplateApp2, categoryToTemplateApp2

admin.site.register([taskApp2, templateApp2, facetemplateApp2, categoryToTemplateApp2])
