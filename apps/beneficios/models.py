import uuid
from django.db import models
from apps.core.models import TimeStampedUUIDModel


class BeneficiosReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_external_id = models.UUIDField(db_column="user_id", null=True, blank=True)
    directorate = models.ForeignKey(
        "directorates.Directorate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="beneficios_reports",
    )
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    encaminhadas_inclusao_cadunico = models.IntegerField(null=True, blank=True, default=0)
    encaminhadas_atualizacao_cadunico = models.IntegerField(null=True, blank=True, default=0)
    consulta_cadunico = models.IntegerField(null=True, blank=True, default=0)
    numero_nis = models.IntegerField(null=True, blank=True, default=0)
    dmae = models.IntegerField(null=True, blank=True, default=0)
    pro_pao = models.IntegerField(null=True, blank=True, default=0)
    auxilio_documento = models.IntegerField(null=True, blank=True, default=0)
    carteirinha_idoso = models.IntegerField(null=True, blank=True, default=0)
    bpc_presencial = models.IntegerField(null=True, blank=True, default=0)
    bpc_online = models.IntegerField(null=True, blank=True, default=0)
    solicitacao_colchoes = models.IntegerField(null=True, blank=True, default=0)
    cesta_basica = models.IntegerField(null=True, blank=True, default=0)
    solicitacao_fraldas = models.IntegerField(null=True, blank=True, default=0)
    absorvente = models.IntegerField(null=True, blank=True, default=0)
    agasalho_cobertor = models.IntegerField(null=True, blank=True, default=0)
    visitas_cadunico = models.IntegerField(null=True, blank=True, default=0)
    visita_nucleo_habitacao = models.IntegerField(null=True, blank=True, default=0)
    visita_cesta_fraldas_colchoes = models.IntegerField(null=True, blank=True, default=0)
    visita_dmae = models.IntegerField(null=True, blank=True, default=0)
    visitas_pro_pao = models.IntegerField(null=True, blank=True, default=0)
    total_visitas = models.IntegerField(null=True, blank=True, default=0)
    busao_social_1 = models.IntegerField(null=True, blank=True, default=0)
    busao_social_2 = models.IntegerField(null=True, blank=True, default=0)
    dibs = models.IntegerField(null=True, blank=True, default=0)
    familias_pbf = models.IntegerField(null=True, blank=True, default=0)
    pessoas_cadunico = models.IntegerField(null=True, blank=True, default=0)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "beneficios_reports"
        managed = False
        unique_together = ("directorate", "month", "year")
        ordering = ["-year", "-month", "-updated_at"]
        verbose_name = "Relatorio Beneficios"
        verbose_name_plural = "Relatorios Beneficios"
