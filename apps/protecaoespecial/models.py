import uuid
from django.db import models


class CreasProtetivoReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    directorate = models.ForeignKey(
        "directorates.Directorate", on_delete=models.CASCADE, null=True, blank=True,
        related_name="creas_protetivo_reports",
    )
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default="draft")
    user_id = models.UUIDField(null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True)

    # Famílias
    fam_mes_anterior = models.IntegerField(null=True, blank=True, default=0)
    fam_admitidas = models.IntegerField(null=True, blank=True, default=0)
    fam_desligadas = models.IntegerField(null=True, blank=True, default=0)
    fam_atual = models.IntegerField(null=True, blank=True, default=0)

    # Direitos Violados
    viol_fis_psic_masc = models.IntegerField(null=True, blank=True, default=0)
    viol_fis_psic_fem = models.IntegerField(null=True, blank=True, default=0)
    abuso_sexual_masc = models.IntegerField(null=True, blank=True, default=0)
    abuso_sexual_fem = models.IntegerField(null=True, blank=True, default=0)
    expl_sexual_masc = models.IntegerField(null=True, blank=True, default=0)
    expl_sexual_fem = models.IntegerField(null=True, blank=True, default=0)
    negli_aband_masc = models.IntegerField(null=True, blank=True, default=0)
    negli_aband_fem = models.IntegerField(null=True, blank=True, default=0)
    trab_infantil_masc = models.IntegerField(null=True, blank=True, default=0)
    trab_infantil_fem = models.IntegerField(null=True, blank=True, default=0)

    # Atendimentos
    atend_mes_anterior = models.IntegerField(null=True, blank=True, default=0)
    atend_admitidas = models.IntegerField(null=True, blank=True, default=0)
    atend_desligadas = models.IntegerField(null=True, blank=True, default=0)
    atend_atual = models.IntegerField(null=True, blank=True, default=0)

    class Meta:
        db_table = "creas_protetivo_reports"
        managed = False
        unique_together = ("directorate", "month", "year")
        ordering = ["-year", "-month", "-updated_at"]
        verbose_name = "Relatório CREAS Protetivo"
        verbose_name_plural = "Relatórios CREAS Protetivo"

    def save(self, *args, **kwargs):
        # Auto-compute totals
        self.fam_atual = (self.fam_mes_anterior or 0) + (self.fam_admitidas or 0) - (self.fam_desligadas or 0)
        self.atend_atual = (self.atend_mes_anterior or 0) + (self.atend_admitidas or 0) - (self.atend_desligadas or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"CREAS Protetivo - {self.month}/{self.year}"


class CreasSocioeducativoReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    directorate = models.ForeignKey(
        "directorates.Directorate", on_delete=models.CASCADE, null=True, blank=True,
        related_name="creas_socioeducativo_reports",
    )
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default="draft")
    user_id = models.UUIDField(null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True)

    # Famílias
    fam_acompanhamento_1_dia = models.IntegerField(null=True, blank=True, default=0)
    fam_inseridas = models.IntegerField(null=True, blank=True, default=0)
    fam_desligadas = models.IntegerField(null=True, blank=True, default=0)
    fam_total_acompanhamento = models.IntegerField(null=True, blank=True, default=0)

    # Acompanhamento Masculino
    masc_acompanhamento_1_dia = models.IntegerField(null=True, blank=True, default=0)
    masc_admitidos = models.IntegerField(null=True, blank=True, default=0)
    masc_desligados = models.IntegerField(null=True, blank=True, default=0)
    masc_total_parcial = models.IntegerField(null=True, blank=True, default=0)

    # Acompanhamento Feminino
    fem_acompanhamento_1_dia = models.IntegerField(null=True, blank=True, default=0)
    fem_admitidos = models.IntegerField(null=True, blank=True, default=0)
    fem_desligadas = models.IntegerField(null=True, blank=True, default=0)
    fem_total_parcial = models.IntegerField(null=True, blank=True, default=0)

    # Medidas Masculino
    med_masc_la_andamento = models.IntegerField(null=True, blank=True, default=0)
    med_masc_psc_andamento = models.IntegerField(null=True, blank=True, default=0)
    med_masc_la_novas = models.IntegerField(null=True, blank=True, default=0)
    med_masc_psc_novas = models.IntegerField(null=True, blank=True, default=0)
    med_masc_la_encerradas = models.IntegerField(null=True, blank=True, default=0)
    med_masc_psc_encerradas = models.IntegerField(null=True, blank=True, default=0)
    med_masc_la_total_parcial = models.IntegerField(null=True, blank=True, default=0)
    med_masc_psc_total_parcial = models.IntegerField(null=True, blank=True, default=0)

    # Medidas Feminino
    med_fem_la_andamento = models.IntegerField(null=True, blank=True, default=0)
    med_fem_psc_andamento = models.IntegerField(null=True, blank=True, default=0)
    med_fem_la_novas = models.IntegerField(null=True, blank=True, default=0)
    med_fem_psc_novas = models.IntegerField(null=True, blank=True, default=0)
    med_fem_la_encerradas = models.IntegerField(null=True, blank=True, default=0)
    med_fem_psc_encerradas = models.IntegerField(null=True, blank=True, default=0)
    med_fem_la_total_parcial = models.IntegerField(null=True, blank=True, default=0)
    med_fem_psc_total_parcial = models.IntegerField(null=True, blank=True, default=0)

    # Totais Gerais
    med_total_la_geral = models.IntegerField(null=True, blank=True, default=0)
    med_total_psc_geral = models.IntegerField(null=True, blank=True, default=0)

    class Meta:
        db_table = "creas_socioeducativo_reports"
        managed = False
        unique_together = ("directorate", "month", "year")
        ordering = ["-year", "-month", "-updated_at"]
        verbose_name = "Relatório CREAS Socioeducativo"
        verbose_name_plural = "Relatórios CREAS Socioeducativo"

    def save(self, *args, **kwargs):
        # Auto-compute totals
        self.fam_total_acompanhamento = (self.fam_acompanhamento_1_dia or 0) + (self.fam_inseridas or 0) - (self.fam_desligadas or 0)
        self.masc_total_parcial = (self.masc_acompanhamento_1_dia or 0) + (self.masc_admitidos or 0) - (self.masc_desligados or 0)
        self.fem_total_parcial = (self.fem_acompanhamento_1_dia or 0) + (self.fem_admitidos or 0) - (self.fem_desligadas or 0)
        
        self.med_masc_la_total_parcial = (self.med_masc_la_andamento or 0) + (self.med_masc_la_novas or 0) - (self.med_masc_la_encerradas or 0)
        self.med_masc_psc_total_parcial = (self.med_masc_psc_andamento or 0) + (self.med_masc_psc_novas or 0) - (self.med_masc_psc_encerradas or 0)
        
        self.med_fem_la_total_parcial = (self.med_fem_la_andamento or 0) + (self.med_fem_la_novas or 0) - (self.med_fem_la_encerradas or 0)
        self.med_fem_psc_total_parcial = (self.med_fem_psc_andamento or 0) + (self.med_fem_psc_novas or 0) - (self.med_fem_psc_encerradas or 0)
        
        self.med_total_la_geral = (self.med_masc_la_total_parcial or 0) + (self.med_fem_la_total_parcial or 0)
        self.med_total_psc_geral = (self.med_masc_psc_total_parcial or 0) + (self.med_fem_psc_total_parcial or 0)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"CREAS Socioeducativo - {self.month}/{self.year}"
