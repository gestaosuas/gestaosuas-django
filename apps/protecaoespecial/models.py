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

    fam_mes_anterior = models.IntegerField(null=True, blank=True, default=0)
    fam_admitidas = models.IntegerField(null=True, blank=True, default=0)
    fam_desligadas = models.IntegerField(null=True, blank=True, default=0)
    fam_atual = models.IntegerField(null=True, blank=True, default=0)

    # 90 campos de violações — 5 tipos × 3 subcategorias × 6 gender-age
    # Pref: vf=violencia fisica, as=abuso sexual, es=exploracao sexual, ng=negligencia, ti=trabalho infantil
    # Suf: at=atendidas anterior, in=inseridos, de=desligados
    # GA: m0=masc 0-6, m7=masc 7-12, m13=masc 13-17, f0=fem 0-6, f7=fem 7-12, f13=fem 13-17

    vf_at_m0 = models.IntegerField(null=True, blank=True, default=0)
    vf_at_m7 = models.IntegerField(null=True, blank=True, default=0)
    vf_at_m13 = models.IntegerField(null=True, blank=True, default=0)
    vf_at_f0 = models.IntegerField(null=True, blank=True, default=0)
    vf_at_f7 = models.IntegerField(null=True, blank=True, default=0)
    vf_at_f13 = models.IntegerField(null=True, blank=True, default=0)
    vf_in_m0 = models.IntegerField(null=True, blank=True, default=0)
    vf_in_m7 = models.IntegerField(null=True, blank=True, default=0)
    vf_in_m13 = models.IntegerField(null=True, blank=True, default=0)
    vf_in_f0 = models.IntegerField(null=True, blank=True, default=0)
    vf_in_f7 = models.IntegerField(null=True, blank=True, default=0)
    vf_in_f13 = models.IntegerField(null=True, blank=True, default=0)
    vf_de_m0 = models.IntegerField(null=True, blank=True, default=0)
    vf_de_m7 = models.IntegerField(null=True, blank=True, default=0)
    vf_de_m13 = models.IntegerField(null=True, blank=True, default=0)
    vf_de_f0 = models.IntegerField(null=True, blank=True, default=0)
    vf_de_f7 = models.IntegerField(null=True, blank=True, default=0)
    vf_de_f13 = models.IntegerField(null=True, blank=True, default=0)

    as_at_m0 = models.IntegerField(null=True, blank=True, default=0)
    as_at_m7 = models.IntegerField(null=True, blank=True, default=0)
    as_at_m13 = models.IntegerField(null=True, blank=True, default=0)
    as_at_f0 = models.IntegerField(null=True, blank=True, default=0)
    as_at_f7 = models.IntegerField(null=True, blank=True, default=0)
    as_at_f13 = models.IntegerField(null=True, blank=True, default=0)
    as_in_m0 = models.IntegerField(null=True, blank=True, default=0)
    as_in_m7 = models.IntegerField(null=True, blank=True, default=0)
    as_in_m13 = models.IntegerField(null=True, blank=True, default=0)
    as_in_f0 = models.IntegerField(null=True, blank=True, default=0)
    as_in_f7 = models.IntegerField(null=True, blank=True, default=0)
    as_in_f13 = models.IntegerField(null=True, blank=True, default=0)
    as_de_m0 = models.IntegerField(null=True, blank=True, default=0)
    as_de_m7 = models.IntegerField(null=True, blank=True, default=0)
    as_de_m13 = models.IntegerField(null=True, blank=True, default=0)
    as_de_f0 = models.IntegerField(null=True, blank=True, default=0)
    as_de_f7 = models.IntegerField(null=True, blank=True, default=0)
    as_de_f13 = models.IntegerField(null=True, blank=True, default=0)

    es_at_m0 = models.IntegerField(null=True, blank=True, default=0)
    es_at_m7 = models.IntegerField(null=True, blank=True, default=0)
    es_at_m13 = models.IntegerField(null=True, blank=True, default=0)
    es_at_f0 = models.IntegerField(null=True, blank=True, default=0)
    es_at_f7 = models.IntegerField(null=True, blank=True, default=0)
    es_at_f13 = models.IntegerField(null=True, blank=True, default=0)
    es_in_m0 = models.IntegerField(null=True, blank=True, default=0)
    es_in_m7 = models.IntegerField(null=True, blank=True, default=0)
    es_in_m13 = models.IntegerField(null=True, blank=True, default=0)
    es_in_f0 = models.IntegerField(null=True, blank=True, default=0)
    es_in_f7 = models.IntegerField(null=True, blank=True, default=0)
    es_in_f13 = models.IntegerField(null=True, blank=True, default=0)
    es_de_m0 = models.IntegerField(null=True, blank=True, default=0)
    es_de_m7 = models.IntegerField(null=True, blank=True, default=0)
    es_de_m13 = models.IntegerField(null=True, blank=True, default=0)
    es_de_f0 = models.IntegerField(null=True, blank=True, default=0)
    es_de_f7 = models.IntegerField(null=True, blank=True, default=0)
    es_de_f13 = models.IntegerField(null=True, blank=True, default=0)

    ng_at_m0 = models.IntegerField(null=True, blank=True, default=0)
    ng_at_m7 = models.IntegerField(null=True, blank=True, default=0)
    ng_at_m13 = models.IntegerField(null=True, blank=True, default=0)
    ng_at_f0 = models.IntegerField(null=True, blank=True, default=0)
    ng_at_f7 = models.IntegerField(null=True, blank=True, default=0)
    ng_at_f13 = models.IntegerField(null=True, blank=True, default=0)
    ng_in_m0 = models.IntegerField(null=True, blank=True, default=0)
    ng_in_m7 = models.IntegerField(null=True, blank=True, default=0)
    ng_in_m13 = models.IntegerField(null=True, blank=True, default=0)
    ng_in_f0 = models.IntegerField(null=True, blank=True, default=0)
    ng_in_f7 = models.IntegerField(null=True, blank=True, default=0)
    ng_in_f13 = models.IntegerField(null=True, blank=True, default=0)
    ng_de_m0 = models.IntegerField(null=True, blank=True, default=0)
    ng_de_m7 = models.IntegerField(null=True, blank=True, default=0)
    ng_de_m13 = models.IntegerField(null=True, blank=True, default=0)
    ng_de_f0 = models.IntegerField(null=True, blank=True, default=0)
    ng_de_f7 = models.IntegerField(null=True, blank=True, default=0)
    ng_de_f13 = models.IntegerField(null=True, blank=True, default=0)

    ti_at_m0 = models.IntegerField(null=True, blank=True, default=0)
    ti_at_m7 = models.IntegerField(null=True, blank=True, default=0)
    ti_at_m13 = models.IntegerField(null=True, blank=True, default=0)
    ti_at_f0 = models.IntegerField(null=True, blank=True, default=0)
    ti_at_f7 = models.IntegerField(null=True, blank=True, default=0)
    ti_at_f13 = models.IntegerField(null=True, blank=True, default=0)
    ti_in_m0 = models.IntegerField(null=True, blank=True, default=0)
    ti_in_m7 = models.IntegerField(null=True, blank=True, default=0)
    ti_in_m13 = models.IntegerField(null=True, blank=True, default=0)
    ti_in_f0 = models.IntegerField(null=True, blank=True, default=0)
    ti_in_f7 = models.IntegerField(null=True, blank=True, default=0)
    ti_in_f13 = models.IntegerField(null=True, blank=True, default=0)
    ti_de_m0 = models.IntegerField(null=True, blank=True, default=0)
    ti_de_m7 = models.IntegerField(null=True, blank=True, default=0)
    ti_de_m13 = models.IntegerField(null=True, blank=True, default=0)
    ti_de_f0 = models.IntegerField(null=True, blank=True, default=0)
    ti_de_f7 = models.IntegerField(null=True, blank=True, default=0)
    ti_de_f13 = models.IntegerField(null=True, blank=True, default=0)

    class Meta:
        db_table = "creas_protetivo_reports"
        managed = False
        unique_together = ("directorate", "month", "year")
        ordering = ["-year", "-month", "-updated_at"]
        verbose_name = "Relatório CREAS Protetivo"
        verbose_name_plural = "Relatórios CREAS Protetivo"

    def save(self, *args, **kwargs):
        self.fam_atual = (self.fam_mes_anterior or 0) + (self.fam_admitidas or 0)
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

    fam_acompanhamento_1_dia = models.IntegerField(null=True, blank=True, default=0)
    fam_inseridas = models.IntegerField(null=True, blank=True, default=0)
    fam_desligadas = models.IntegerField(null=True, blank=True, default=0)
    fam_total_acompanhamento = models.IntegerField(null=True, blank=True, default=0)

    masc_acompanhamento_1_dia = models.IntegerField(null=True, blank=True, default=0)
    masc_admitidos = models.IntegerField(null=True, blank=True, default=0)
    masc_desligados = models.IntegerField(null=True, blank=True, default=0)
    masc_total_parcial = models.IntegerField(null=True, blank=True, default=0)

    fem_acompanhamento_1_dia = models.IntegerField(null=True, blank=True, default=0)
    fem_admitidos = models.IntegerField(null=True, blank=True, default=0)
    fem_desligadas = models.IntegerField(null=True, blank=True, default=0)
    fem_total_parcial = models.IntegerField(null=True, blank=True, default=0)

    med_masc_la_andamento = models.IntegerField(null=True, blank=True, default=0)
    med_masc_psc_andamento = models.IntegerField(null=True, blank=True, default=0)
    med_masc_la_novas = models.IntegerField(null=True, blank=True, default=0)
    med_masc_psc_novas = models.IntegerField(null=True, blank=True, default=0)
    med_masc_la_encerradas = models.IntegerField(null=True, blank=True, default=0)
    med_masc_psc_encerradas = models.IntegerField(null=True, blank=True, default=0)
    med_masc_la_total_parcial = models.IntegerField(null=True, blank=True, default=0)
    med_masc_psc_total_parcial = models.IntegerField(null=True, blank=True, default=0)

    med_fem_la_andamento = models.IntegerField(null=True, blank=True, default=0)
    med_fem_psc_andamento = models.IntegerField(null=True, blank=True, default=0)
    med_fem_la_novas = models.IntegerField(null=True, blank=True, default=0)
    med_fem_psc_novas = models.IntegerField(null=True, blank=True, default=0)
    med_fem_la_encerradas = models.IntegerField(null=True, blank=True, default=0)
    med_fem_psc_encerradas = models.IntegerField(null=True, blank=True, default=0)
    med_fem_la_total_parcial = models.IntegerField(null=True, blank=True, default=0)
    med_fem_psc_total_parcial = models.IntegerField(null=True, blank=True, default=0)

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
