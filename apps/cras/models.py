import uuid
from django.db import models
from apps.core.models import DirectorateMonthlyReportBase


class CrasReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_external_id = models.UUIDField(db_column="user_id", null=True, blank=True)
    directorate = models.ForeignKey(
        "directorates.Directorate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cras_reports",
    )
    unit_name = models.TextField()
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    mes_anterior = models.IntegerField(null=True, blank=True, default=0)
    admitidas = models.IntegerField(null=True, blank=True, default=0)
    desligadas = models.IntegerField(null=True, blank=True, default=0)
    atual = models.IntegerField(null=True, blank=True, default=0)
    atendimentos = models.IntegerField(null=True, blank=True, default=0)
    visita_domiciliar = models.IntegerField(null=True, blank=True, default=0)
    atend_particularizado = models.IntegerField(null=True, blank=True, default=0)
    pro_pao = models.IntegerField(null=True, blank=True, default=0)
    dmae = models.IntegerField(null=True, blank=True, default=0)
    auxilio_documento = models.IntegerField(null=True, blank=True, default=0)
    cesta_basica = models.IntegerField(null=True, blank=True, default=0)
    fralda = models.IntegerField(null=True, blank=True, default=0)
    absorvente = models.IntegerField(null=True, blank=True, default=0)
    bpc = models.IntegerField(null=True, blank=True, default=0)
    carteirinha_idoso = models.IntegerField(null=True, blank=True, default=0)
    passe_livre_deficiente = models.IntegerField(null=True, blank=True, default=0)
    cadastros_novos = models.IntegerField(null=True, blank=True, default=0)
    recadastros = models.IntegerField(null=True, blank=True, default=0)
    rma_url = models.TextField(null=True, blank=True)
    anexo_rma = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "cras_reports"
        managed = False
        unique_together = ("directorate", "unit_name", "month", "year")
        ordering = ["-year", "-month", "unit_name", "-updated_at"]
        verbose_name = "Relatorio CRAS"
        verbose_name_plural = "Relatorios CRAS"
