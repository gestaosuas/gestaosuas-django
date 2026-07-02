import uuid

from django.conf import settings
from django.db import models


class TimeStampedUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DirectorateMonthlyReportBase(TimeStampedUUIDModel):
    STATUS_CHOICES = [("draft", "Rascunho"), ("finalized", "Finalizado"), ("submitted", "Enviado")]

    directorate = models.ForeignKey("directorates.Directorate", on_delete=models.CASCADE)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    user_id = models.UUIDField(null=True, blank=True)
    created_by = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True
        ordering = ["-year", "-month", "-updated_at"]


class SystemSetting(models.Model):
    key = models.CharField(max_length=120, primary_key=True)
    value = models.TextField(blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settings"
        managed = False
        verbose_name = "Configuracao do sistema"
        verbose_name_plural = "Configuracoes do sistema"

    def __str__(self) -> str:
        return self.key


class ActivityLog(TimeStampedUUIDModel):
    user_id = models.UUIDField(null=True, blank=True)
    user_name = models.CharField(max_length=255, blank=True)
    directorate = models.ForeignKey(
        "directorates.Directorate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    directorate_name = models.CharField(max_length=255, blank=True)
    action_type = models.CharField(max_length=120)
    resource_type = models.CharField(max_length=120)
    resource_name = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "activity_logs"
        managed = False
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action_type} - {self.resource_type}"


class MapCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    color = models.CharField(max_length=40, default="gray")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "map_categories"
        managed = False
        verbose_name = "Categoria de mapa"
        verbose_name_plural = "Categorias de mapa"

    def __str__(self) -> str:
        return self.name


class MapUnit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        MapCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="units",
    )
    name = models.CharField(max_length=255)
    region = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=60, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "map_units"
        managed = False
        verbose_name = "Unidade do mapa"
        verbose_name_plural = "Unidades do mapa"

    def __str__(self) -> str:
        return self.name
