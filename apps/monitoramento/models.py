import uuid

from django.db import models

from apps.core.models import TimeStampedUUIDModel, DirectorateMonthlyReportBase















class GenericMonitoringReport(DirectorateMonthlyReportBase):
    reference = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)

    class Meta(DirectorateMonthlyReportBase.Meta):
        db_table = "monitorings_genericmonitoringreport"
        managed = False
        unique_together = ("directorate", "reference", "month", "year")
        verbose_name = "Relatorio de monitoramento"
        verbose_name_plural = "Relatorios de monitoramento"
