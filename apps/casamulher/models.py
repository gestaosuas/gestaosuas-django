import uuid
from django.db import models
from apps.directorates.models import Directorate

class CasaDaMulherReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    directorate = models.ForeignKey(Directorate, on_delete=models.DO_NOTHING, db_column='directorate_id')
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=50, default="draft")
    user_id = models.UUIDField()
    created_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    # Atendimentos
    cm_atend_mulheres_atendidas = models.IntegerField(null=True, blank=True, default=0)
    
    # Faixa etaria
    cm_faixa_16_17 = models.IntegerField(null=True, blank=True, default=0)
    cm_faixa_18_30 = models.IntegerField(null=True, blank=True, default=0)
    cm_faixa_31_40 = models.IntegerField(null=True, blank=True, default=0)
    cm_faixa_41_50 = models.IntegerField(null=True, blank=True, default=0)
    cm_faixa_51_60 = models.IntegerField(null=True, blank=True, default=0)
    cm_faixa_acima_60 = models.IntegerField(null=True, blank=True, default=0)
    cm_faixa_nao_consta = models.IntegerField(null=True, blank=True, default=0)
    
    # Raca/cor
    cm_raca_branca = models.IntegerField(null=True, blank=True, default=0)
    cm_raca_preta = models.IntegerField(null=True, blank=True, default=0)
    cm_raca_parda = models.IntegerField(null=True, blank=True, default=0)
    cm_raca_amarelo = models.IntegerField(null=True, blank=True, default=0)
    cm_raca_indigena = models.IntegerField(null=True, blank=True, default=0)
    cm_raca_nao_consta = models.IntegerField(null=True, blank=True, default=0)
    
    # Violencia
    cm_violencia_fisica = models.IntegerField(null=True, blank=True, default=0)
    cm_violencia_moral = models.IntegerField(null=True, blank=True, default=0)
    cm_violencia_psicologica = models.IntegerField(null=True, blank=True, default=0)
    cm_violencia_sexual = models.IntegerField(null=True, blank=True, default=0)
    cm_violencia_patrimonial = models.IntegerField(null=True, blank=True, default=0)
    cm_violencia_nenhuma = models.IntegerField(null=True, blank=True, default=0)
    cm_violencia_outras = models.IntegerField(null=True, blank=True, default=0)
    
    # Encaminhamentos
    cm_encam_bo_ocorrencia = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_casa_abrigo = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_conselho_idoso = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_conselho_tutelar = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_defens_publica = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_forum_juizados = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_exame_c_delito = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_deam = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_ministerio_publico = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_outra_delegacia = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_ppvd = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_rede_ass_social = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_rede_saude = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_sine = models.IntegerField(null=True, blank=True, default=0)
    cm_encam_outros = models.IntegerField(null=True, blank=True, default=0)

    class Meta:
        db_table = "casa_da_mulher_reports"
        managed = False

    def __str__(self):
        return f"Casa da Mulher Report {self.year}-{self.month}"


class DiversidadeReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    directorate = models.ForeignKey(Directorate, on_delete=models.DO_NOTHING, db_column='directorate_id')
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=50, default="draft")
    user_id = models.UUIDField()
    created_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    # Atendimento
    div_atend_mulheres_atendidas = models.IntegerField(null=True, blank=True, default=0)
    div_atend_nucleo_diversidade = models.IntegerField(null=True, blank=True, default=0)
    
    # Faixas
    div_faixa_16_17 = models.IntegerField(null=True, blank=True, default=0)
    div_faixa_18_30 = models.IntegerField(null=True, blank=True, default=0)
    div_faixa_31_40 = models.IntegerField(null=True, blank=True, default=0)
    div_faixa_41_50 = models.IntegerField(null=True, blank=True, default=0)
    div_faixa_51_60 = models.IntegerField(null=True, blank=True, default=0)
    div_faixa_acima_60 = models.IntegerField(null=True, blank=True, default=0)
    div_faixa_nao_consta = models.IntegerField(null=True, blank=True, default=0)
    
    # Raca
    div_raca_branca = models.IntegerField(null=True, blank=True, default=0)
    div_raca_preta = models.IntegerField(null=True, blank=True, default=0)
    div_raca_parda = models.IntegerField(null=True, blank=True, default=0)
    div_raca_amarela = models.IntegerField(null=True, blank=True, default=0)
    div_raca_indigena = models.IntegerField(null=True, blank=True, default=0)
    div_raca_nao_consta = models.IntegerField(null=True, blank=True, default=0)
    
    # Demanda
    div_sit_violencia_infrafamiliar = models.IntegerField(null=True, blank=True, default=0)
    div_sit_violencia_extrafamiliar = models.IntegerField(null=True, blank=True, default=0)
    div_sit_demanda_fora_contexto = models.IntegerField(null=True, blank=True, default=0)
    
    # Encaminhamentos
    div_encam_juizado = models.IntegerField(null=True, blank=True, default=0)
    div_encam_rede_socioassist = models.IntegerField(null=True, blank=True, default=0)
    div_encam_curso_prof = models.IntegerField(null=True, blank=True, default=0)
    div_encam_sine = models.IntegerField(null=True, blank=True, default=0)
    div_encam_serv_saude = models.IntegerField(null=True, blank=True, default=0)
    div_encam_mobilizacao_familia = models.IntegerField(null=True, blank=True, default=0)
    div_encam_orient_juridicas = models.IntegerField(null=True, blank=True, default=0)
    div_encam_bo_reds = models.IntegerField(null=True, blank=True, default=0)
    div_encam_exame_delito = models.IntegerField(null=True, blank=True, default=0)
    div_encam_outros = models.IntegerField(null=True, blank=True, default=0)

    class Meta:
        db_table = "diversidade_reports"
        managed = False

    def __str__(self):
        return f"Diversidade Report {self.year}-{self.month}"


class NucleoDiversidadeReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    directorate = models.ForeignKey(Directorate, on_delete=models.DO_NOTHING, db_column='directorate_id')
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=50, default="draft")
    user_id = models.UUIDField()
    created_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    # Atendimentos
    nd_pessoas_atendidas = models.IntegerField(null=True, blank=True, default=0)

    class Meta:
        db_table = "nucleo_diversidade_reports"
        managed = False

    def __str__(self):
        return f"Núcleo Diversidade Report {self.year}-{self.month}"
