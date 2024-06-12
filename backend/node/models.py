from django.db import models

class taskApp2(models.Model):
    class Meta:
        db_table = 'taskApp2'

    task_id = models.CharField(max_length=500, unique=True)
    status = models.CharField(max_length=50)
    server = models.CharField(max_length=100)
    template_id = models.IntegerField()
    decoded_image = models.CharField(max_length=500, default=None)
    source = models.CharField(max_length=500, default=None)
    thumb = models.CharField(max_length=500, null=True, blank=True)
    preview_source = models.CharField(max_length=500, null=True, blank=True)
    watermark = models.BooleanField(default=True)
    timer = models.PositiveIntegerField(default=None)
    is_image = models.BooleanField()
    new = models.BooleanField()
    premium = models.BooleanField(default=False)

    def __str__(self):
        return str(self.task_id) + ' ' + str(self.template_id) + ' ' + str(self.source) + ' ' + str(self.status)


class templateApp2(models.Model):
    class Meta:
        db_table = 'templateApp2'

    sort_id = models.IntegerField()
    source = models.CharField(max_length=500, default=None)
    thumb = models.CharField(max_length=500, null=True, blank=True)
    preview_source = models.CharField(max_length=500, null=True, blank=True)
    premium = models.BooleanField(default=False)

    def __str__(self):
        return str(self.sort_id) + ' ' + str(self.source)


class facetemplateApp2(models.Model):
    class Meta:
        db_table = 'facetemplateApp2'

    template_id = models.PositiveIntegerField()
    source = models.CharField(max_length=500, default=None)

    def __str__(self):
        return str(self.template_id) + ' ' + str(self.source)


class categoryToTemplateApp2(models.Model):
    class Meta:
        db_table = 'categoryToTemplateApp2'

    templ_id = models.PositiveIntegerField()
    category_int = models.PositiveIntegerField()

    def __str__(self):
        return str(self.templ_id) + ' ' + str(self.category_int)
    