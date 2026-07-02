import uuid
from django.db import models
from apps.accounts.models import User
from apps.directorates.models import Directorate

class PopRuaReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    directorate = models.ForeignKey(
        Directorate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="pop_rua_reports",
        db_column="directorate_id"
    )
    month = models.PositiveSmallIntegerField(verbose_name="Mês")
    year = models.PositiveIntegerField(verbose_name="Ano")
    status = models.TextField(default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, db_column="created_by")

    # Atendimentos
    num_atend_centro_ref = models.IntegerField(default=0, verbose_name="Centro de Referência")
    num_atend_abordagem = models.IntegerField(default=0, verbose_name="Abordagem Social")
    num_atend_migracao = models.IntegerField(default=0, verbose_name="Migração")
    num_atend_total = models.IntegerField(default=0, verbose_name="Total")

    # Centro de Referência
    cr_a1_masc = models.IntegerField(default=0, verbose_name="A.1 Centro Especializado para Pessoas em Situação de Rua Masculino")
    cr_a1_fem = models.IntegerField(default=0, verbose_name="A.1 Centro Especializado para Pessoas em Situação de Rua Feminino")
    cr_b1_drogas = models.IntegerField(default=0, verbose_name="B.1 Usuários de drogas")
    cr_b2_migrantes = models.IntegerField(default=0, verbose_name="B.2 Pessoas Consideradas Migrantes/Trecheiros")
    cr_b3_mental = models.IntegerField(default=0, verbose_name="B.3 Doença ou transtorno Psiquiatrico (Mental)")
    cr_cad_unico = models.IntegerField(default=0, verbose_name="Pessoas cadastradas no Cad Único")
    cr_enc_mercado = models.IntegerField(default=0, verbose_name="Pessoas encaminhadas para o mercado de trabalho")
    cr_enc_caps = models.IntegerField(default=0, verbose_name="Pessoas encaminhadas para CAPs AD e Saúde Mental")
    cr_enc_saude = models.IntegerField(default=0, verbose_name="Pessoas encaminhadas para a Saúde Pública (UAI/UBS)")
    cr_enc_consultorio = models.IntegerField(default=0, verbose_name="Pessoas encaminhadas para Consultório na Rua")
    cr_segunda_via = models.IntegerField(default=0, verbose_name="Segunda via de Documentação")

    # Abordagem
    ar_e1_masc = models.IntegerField(default=0, verbose_name="E.1 Abordagem Social Masculino")
    ar_e2_fem = models.IntegerField(default=0, verbose_name="E.2 Abordagem Social Feminino")
    ar_e5_drogas = models.IntegerField(default=0, verbose_name="E.5 Usuários de drogas")
    ar_e6_migrantes = models.IntegerField(default=0, verbose_name="E.6 Migrantes")
    ar_persistentes = models.IntegerField(default=0, verbose_name="Usuários que persistem em continuar nas ruas")
    ar_enc_centro_ref = models.IntegerField(default=0, verbose_name="Nº de encaminhamentos para o Centro de Referência")
    ar_recusa_identificacao = models.IntegerField(default=0, verbose_name="Nº de pessoas que se recusaram a ser identificadas")

    # Núcleo do Migrante
    nm_total_passagens = models.IntegerField(default=0, verbose_name="Total de Usuários que pleitearam passagens")
    nm_passagens_deferidas = models.IntegerField(default=0, verbose_name="Passagens Deferidas")
    nm_passagens_indeferidas = models.IntegerField(default=0, verbose_name="Passagens Indeferidas")
    nm_estrangeiros = models.IntegerField(default=0, verbose_name="Pessoas Estrangeiras")
    nm_retorno_familiar = models.IntegerField(default=0, verbose_name="Pessoas que retornaram para o Núcleo Familiar")
    nm_busca_trabalho = models.IntegerField(default=0, verbose_name="Pessoas em busca de trabalho")
    nm_busca_saude = models.IntegerField(default=0, verbose_name="Pessoas em busca de tratamento de saúde")

    class Meta:
        db_table = "creas_pop_rua_reports"
        managed = False
        unique_together = ("directorate", "month", "year")
        verbose_name = "Relatório PopRua"
        verbose_name_plural = "Relatórios PopRua"

    def __str__(self):
        return f"PopRua {self.month}/{self.year}"
