import uuid
from django.db import models


class SineReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_external_id = models.UUIDField(db_column="user_id", null=True, blank=True)
    directorate = models.ForeignKey(
        "directorates.Directorate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sine_reports",
    )
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    atend_trabalhador = models.IntegerField(null=True, blank=True, default=0)
    atend_online_trabalhador = models.IntegerField(null=True, blank=True, default=0)
    atend_empregador = models.IntegerField(null=True, blank=True, default=0)
    atend_online_empregador = models.IntegerField(null=True, blank=True, default=0)
    seguro_desemprego = models.IntegerField(null=True, blank=True, default=0)
    vagas_captadas = models.IntegerField(null=True, blank=True, default=0)
    ligacoes_recebidas = models.IntegerField(null=True, blank=True, default=0)
    ligacoes_realizadas = models.IntegerField(null=True, blank=True, default=0)
    curriculos = models.IntegerField(null=True, blank=True, default=0)
    entrevistados = models.IntegerField(null=True, blank=True, default=0)
    proc_administrativos = models.IntegerField(null=True, blank=True, default=0)
    processo_seletivo = models.IntegerField(null=True, blank=True, default=0)
    inseridos_mercado = models.IntegerField(null=True, blank=True, default=0)
    carteira_digital = models.IntegerField(null=True, blank=True, default=0)
    orientacao_profissional = models.IntegerField(null=True, blank=True, default=0)
    convocacao_trabalhadores = models.IntegerField(null=True, blank=True, default=0)
    vagas_alto_valor = models.IntegerField(null=True, blank=True, default=0)
    atendimentos = models.IntegerField(null=True, blank=True, default=0)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sine_reports"
        managed = False
        unique_together = ("month", "year")
        ordering = ["-year", "-month", "-updated_at"]
        verbose_name = "Relatorio SINE"
        verbose_name_plural = "Relatorios SINE"


class QualificacaoReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_external_id = models.UUIDField(db_column="user_id", null=True, blank=True)
    directorate = models.ForeignKey(
        "directorates.Directorate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="qualificacao_reports",
    )
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    resumo_vagas = models.IntegerField(null=True, blank=True, default=0)
    resumo_cursos = models.IntegerField(null=True, blank=True, default=0)
    resumo_turmas = models.IntegerField(null=True, blank=True, default=0)
    resumo_concluintes = models.IntegerField(null=True, blank=True, default=0)
    resumo_mulheres = models.IntegerField(null=True, blank=True, default=0)
    resumo_homens = models.IntegerField(null=True, blank=True, default=0)
    resumo_mercado_fem = models.IntegerField(null=True, blank=True, default=0)
    resumo_mercado_masc = models.IntegerField(null=True, blank=True, default=0)
    resumo_vagas_ocupadas = models.IntegerField(null=True, blank=True, default=0)
    resumo_taxa_ocupacao = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    cp_morumbi_concluintes = models.IntegerField(null=True, blank=True, default=0)
    cp_lagoinha_concluintes = models.IntegerField(null=True, blank=True, default=0)
    cp_campo_alegre_concluintes = models.IntegerField(null=True, blank=True, default=0)
    cp_luizote_1_concluintes = models.IntegerField(null=True, blank=True, default=0)
    cp_luizote_2_concluintes = models.IntegerField(null=True, blank=True, default=0)
    cp_tocantins_concluintes = models.IntegerField(null=True, blank=True, default=0)
    cp_planalto_concluintes = models.IntegerField(null=True, blank=True, default=0)
    onibus_concluintes_unit = models.IntegerField(null=True, blank=True, default=0)
    maravilha_concluintes = models.IntegerField(null=True, blank=True, default=0)
    uditech_concluintes = models.IntegerField(null=True, blank=True, default=0)
    bairros_visitados = models.IntegerField(null=True, blank=True, default=0)
    concluintes_onibus = models.IntegerField(null=True, blank=True, default=0)
    cursos_onibus = models.IntegerField(null=True, blank=True, default=0)
    cp_morumbi_atendimentos = models.IntegerField(null=True, blank=True, default=0)
    cp_lagoinha_atendimentos = models.IntegerField(null=True, blank=True, default=0)
    cp_campo_alegre_atendimentos = models.IntegerField(null=True, blank=True, default=0)
    cp_luizote_1_atendimentos = models.IntegerField(null=True, blank=True, default=0)
    cp_luizote_2_atendimentos = models.IntegerField(null=True, blank=True, default=0)
    cp_tocantis_atendimentos = models.IntegerField(null=True, blank=True, default=0)
    cp_planalto_atendimentos = models.IntegerField(null=True, blank=True, default=0)
    maravilha_atendimentos = models.IntegerField(null=True, blank=True, default=0)
    unitech_atendimentos = models.IntegerField(null=True, blank=True, default=0)
    onibus_atendimentos = models.IntegerField(null=True, blank=True, default=0)
    cursos_andamento = models.IntegerField(null=True, blank=True, default=0)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "qualificacao_reports"
        managed = False
        unique_together = ("month", "year")
        ordering = ["-year", "-month", "-updated_at"]
        verbose_name = "Relatorio Qualificacao"
        verbose_name_plural = "Relatorios Qualificacao"
