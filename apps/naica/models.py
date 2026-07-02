from django.db import models
from apps.core.models import DirectorateMonthlyReportBase


class NaicaReport(DirectorateMonthlyReportBase):
    unit_name = models.CharField(max_length=255)
    mes_anterior_masc = models.IntegerField(default=0)
    mes_anterior_fem = models.IntegerField(default=0)
    inseridos_masc = models.IntegerField(default=0)
    inseridos_fem = models.IntegerField(default=0)
    desligados_masc = models.IntegerField(default=0)
    desligados_fem = models.IntegerField(default=0)
    total_atendidas = models.IntegerField(default=0)
    atendimentos = models.IntegerField(default=0)

    class Meta(DirectorateMonthlyReportBase.Meta):
        db_table = "naica_reports"
        managed = False
        unique_together = ("directorate", "unit_name", "month", "year")
        verbose_name = "Relatorio NAICA"
        verbose_name_plural = "Relatorios NAICA"
