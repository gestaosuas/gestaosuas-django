import uuid
from django.db import models


class CreasIdosoReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    directorate = models.ForeignKey(
        "directorates.Directorate", on_delete=models.CASCADE, null=True, blank=True,
        related_name="creas_idoso_reports",
    )
    created_by = models.UUIDField(null=True, blank=True)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default="draft")
    paefi_novos_casos = models.IntegerField(null=True, blank=True, default=0)
    paefi_acomp_inicio = models.IntegerField(null=True, blank=True, default=0)
    paefi_inseridos = models.IntegerField(null=True, blank=True, default=0)
    paefi_desligados = models.IntegerField(null=True, blank=True, default=0)
    paefi_bolsa_familia = models.IntegerField(null=True, blank=True, default=0)
    paefi_bpc = models.IntegerField(null=True, blank=True, default=0)
    paefi_substancias = models.IntegerField(null=True, blank=True, default=0)
    violencia_fisica_atendidas_anterior = models.IntegerField(null=True, blank=True, default=0)
    violencia_fisica_inseridos = models.IntegerField(null=True, blank=True, default=0)
    violencia_fisica_desligados = models.IntegerField(null=True, blank=True, default=0)
    violencia_fisica_total = models.IntegerField(null=True, blank=True, default=0)
    abuso_sexual_atendidas_anterior = models.IntegerField(null=True, blank=True, default=0)
    abuso_sexual_inseridos = models.IntegerField(null=True, blank=True, default=0)
    abuso_sexual_desligados = models.IntegerField(null=True, blank=True, default=0)
    abuso_sexual_total = models.IntegerField(null=True, blank=True, default=0)
    exploracao_sexual_atendidas_anterior = models.IntegerField(null=True, blank=True, default=0)
    exploracao_sexual_inseridos = models.IntegerField(null=True, blank=True, default=0)
    exploracao_sexual_desligados = models.IntegerField(null=True, blank=True, default=0)
    exploracao_sexual_total = models.IntegerField(null=True, blank=True, default=0)
    negligencia_atendidas_anterior = models.IntegerField(null=True, blank=True, default=0)
    negligencia_inseridos = models.IntegerField(null=True, blank=True, default=0)
    negligencia_desligados = models.IntegerField(null=True, blank=True, default=0)
    negligencia_total = models.IntegerField(null=True, blank=True, default=0)
    exploracao_financeira_atendidas_anterior = models.IntegerField(null=True, blank=True, default=0)
    exploracao_financeira_inseridos = models.IntegerField(null=True, blank=True, default=0)
    exploracao_financeira_desligados = models.IntegerField(null=True, blank=True, default=0)
    exploracao_financeira_total = models.IntegerField(null=True, blank=True, default=0)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "creas_idoso_reports"
        managed = False
        unique_together = ("directorate", "month", "year")
        ordering = ["-year", "-month", "-updated_at"]
        verbose_name = "Relatorio CREAS Idoso"
        verbose_name_plural = "Relatorios CREAS Idoso"

    def __str__(self):
        return f"CREAS Idoso - {self.month}/{self.year}"


class CreasPcdReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    directorate = models.ForeignKey(
        "directorates.Directorate", on_delete=models.CASCADE, null=True, blank=True,
        related_name="creas_pcd_reports",
    )
    created_by = models.UUIDField(null=True, blank=True)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default="draft")
    def_violencia_fisica_atendidas_anterior = models.IntegerField(null=True, blank=True, default=0)
    def_violencia_fisica_inseridos = models.IntegerField(null=True, blank=True, default=0)
    def_violencia_fisica_desligados = models.IntegerField(null=True, blank=True, default=0)
    def_violencia_fisica_total = models.IntegerField(null=True, blank=True, default=0)
    def_abuso_sexual_atendidas_anterior = models.IntegerField(null=True, blank=True, default=0)
    def_abuso_sexual_inseridos = models.IntegerField(null=True, blank=True, default=0)
    def_abuso_sexual_desligados = models.IntegerField(null=True, blank=True, default=0)
    def_abuso_sexual_total = models.IntegerField(null=True, blank=True, default=0)
    def_exploracao_sexual_atendidas_anterior = models.IntegerField(null=True, blank=True, default=0)
    def_exploracao_sexual_inseridos = models.IntegerField(null=True, blank=True, default=0)
    def_exploracao_sexual_desligados = models.IntegerField(null=True, blank=True, default=0)
    def_exploracao_sexual_total = models.IntegerField(null=True, blank=True, default=0)
    def_negligencia_atendidas_anterior = models.IntegerField(null=True, blank=True, default=0)
    def_negligencia_inseridos = models.IntegerField(null=True, blank=True, default=0)
    def_negligencia_desligados = models.IntegerField(null=True, blank=True, default=0)
    def_negligencia_total = models.IntegerField(null=True, blank=True, default=0)
    def_exploracao_financeira_atendidas_anterior = models.IntegerField(null=True, blank=True, default=0)
    def_exploracao_financeira_inseridos = models.IntegerField(null=True, blank=True, default=0)
    def_exploracao_financeira_desligados = models.IntegerField(null=True, blank=True, default=0)
    def_exploracao_financeira_total = models.IntegerField(null=True, blank=True, default=0)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "creas_pcd_reports"
        managed = False
        unique_together = ("directorate", "month", "year")
        ordering = ["-year", "-month", "-updated_at"]
        verbose_name = "Relatorio CREAS PCD"
        verbose_name_plural = "Relatorios CREAS PCD"

    def __str__(self):
        return f"CREAS PCD - {self.month}/{self.year}"
