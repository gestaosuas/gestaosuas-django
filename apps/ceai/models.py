import uuid
from django.db import models
from apps.accounts.models import User

class CeaiCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    unit = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ceai_categorias'
        verbose_name = 'Categoria CEAI'
        verbose_name_plural = 'Categorias CEAI'

    def __str__(self):
        return f"{self.name} ({self.unit})"

class CeaiOficina(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity_name = models.TextField()
    category = models.ForeignKey(CeaiCategory, on_delete=models.SET_NULL, null=True, related_name='oficinas', db_column='category_id')
    total_vacancies = models.IntegerField(default=0)
    vacancies = models.IntegerField(default=0)  # Occupied slots
    unit = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ceai_oficinas'
        verbose_name = 'Oficina CEAI'
        verbose_name_plural = 'Oficinas CEAI'

    def __str__(self):
        return f"{self.activity_name} ({self.unit})"

class Submission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    directorate_id = models.UUIDField()
    month = models.IntegerField()
    year = models.IntegerField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'submissions'
        verbose_name = 'Submissão'
        verbose_name_plural = 'Submissões'

    def __str__(self):
        return f"Submissão {self.month}/{self.year}"
