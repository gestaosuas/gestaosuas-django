import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedUUIDModel


class Directorate(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.TextField(unique=True)
    sheet_config = models.JSONField(null=True, blank=True)
    form_definition = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    available_units = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "directorates"
        managed = False
        ordering = ["name"]
        verbose_name = "Diretoria"
        verbose_name_plural = "Diretorias"

    def __str__(self) -> str:
        return self.name

    @property
    def slug(self):
        import unicodedata
        import re
        value = unicodedata.normalize('NFD', self.name).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value).strip().lower()
        return re.sub(r'[-\s]+', '-', value)


class MonthlySubmission(models.Model):
    id = models.UUIDField(primary_key=True)
    user_id = models.UUIDField(null=True, blank=True)
    directorate = models.ForeignKey(Directorate, on_delete=models.CASCADE, related_name="submissions")
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "submissions"
        managed = False
        unique_together = ("directorate", "month", "year")
        ordering = ["-year", "-month", "-created_at"]
        verbose_name = "Submissao mensal"
        verbose_name_plural = "Submissoes mensais"

    def __str__(self) -> str:
        return f"{self.directorate} - {self.month}/{self.year}"


class DailyReport(TimeStampedUUIDModel):
    date = models.DateField()
    directorate = models.ForeignKey(Directorate, on_delete=models.CASCADE, related_name="daily_reports")
    data = models.JSONField(default=dict, blank=True)
    user_id = models.UUIDField(null=True, blank=True)
    report_type = models.CharField(max_length=50, blank=True, db_column="type")

    class Meta:
        db_table = "daily_reports"
        managed = False
        unique_together = ("date", "directorate")
        ordering = ["-date", "-updated_at"]
        verbose_name = "Relatorio diario"
        verbose_name_plural = "Relatorios diarios"

    def __str__(self) -> str:
        return f"{self.directorate} - {self.date}"


class MonthlyReport(models.Model):
    STATUS_CHOICES = [("draft", "Rascunho"), ("finalized", "Finalizado"), ("submitted", "Enviado")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_external_id = models.UUIDField(db_column="user_id", null=True, blank=True)
    directorate = models.ForeignKey(Directorate, on_delete=models.CASCADE, related_name="monthly_reports")
    month = models.PositiveSmallIntegerField(null=True, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    setor = models.CharField(max_length=120, blank=True)
    content = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "monthly_reports"
        managed = False
        ordering = ["-year", "-month", "-updated_at"]
        verbose_name = "Relatorio mensal"
        verbose_name_plural = "Relatorios mensais"


class Osc(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    activity_type = models.CharField(max_length=120, blank=True)
    cep = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=20, blank=True)
    neighborhood = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=60, blank=True)
    subsidized_count = models.IntegerField(default=0)
    directorate = models.ForeignKey(Directorate, on_delete=models.CASCADE, related_name="oscs")
    objeto = models.TextField(blank=True)
    objetivos = models.TextField(blank=True)
    metas = models.TextField(blank=True)
    atividades = models.TextField(blank=True)
    user_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "oscs"
        managed = False
        ordering = ["name"]
        verbose_name = "OSC"
        verbose_name_plural = "OSCs"

    def __str__(self) -> str:
        return self.name


class WorkPlan(TimeStampedUUIDModel):
    STATUS_CHOICES = [("draft", "Rascunho"), ("finalized", "Finalizado"), ("submitted", "Enviado")]
    osc = models.ForeignKey(Osc, on_delete=models.CASCADE, related_name="work_plans")
    user_id = models.UUIDField(null=True, blank=True)
    directorate = models.ForeignKey(Directorate, on_delete=models.CASCADE, related_name="work_plans")
    title = models.CharField(max_length=255)
    content = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    class Meta:
        db_table = "work_plans"
        managed = False
        ordering = ["-updated_at", "title"]
        verbose_name = "Plano de trabalho"
        verbose_name_plural = "Planos de trabalho"

    def __str__(self) -> str:
        return self.title


class Visit(TimeStampedUUIDModel):
    STATUS_CHOICES = [("draft", "Rascunho"), ("scheduled", "Agendada"), ("completed", "Concluida")]
    osc = models.ForeignKey(Osc, on_delete=models.CASCADE, related_name="visits")
    directorate = models.ForeignKey(Directorate, on_delete=models.CASCADE, related_name="visits")
    visit_date = models.DateField()
    visit_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    identificacao = models.JSONField(null=True, blank=True)
    atendimento = models.JSONField(null=True, blank=True)
    forma_acesso = models.JSONField(null=True, blank=True)
    rh_data = models.JSONField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    recomendacoes = models.TextField(blank=True)
    assinaturas = models.JSONField(null=True, blank=True)
    parecer_tecnico = models.JSONField(null=True, blank=True)
    parecer_conclusivo = models.JSONField(null=True, blank=True)
    relatorio_final = models.JSONField(null=True, blank=True)
    notificacoes = models.JSONField(default=list, blank=True)
    documents = models.JSONField(default=list, blank=True)
    user_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "visits"
        managed = False
        ordering = ["-visit_date", "-visit_time", "-updated_at"]
        verbose_name = "Visita tecnica"
        verbose_name_plural = "Visitas tecnicas"

    def __str__(self) -> str:
        return f"{self.osc} - {self.visit_date}"


class FormDelegation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey("directorates.Visit", on_delete=models.DO_NOTHING, related_name="delegations", db_column="visit_id")
    user_id = models.UUIDField()
    delegated_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    directorate = models.ForeignKey("directorates.Directorate", on_delete=models.DO_NOTHING, related_name="delegations", db_column="directorate_id")

    class Meta:
        db_table = "form_delegations"
        managed = False
        verbose_name = "Delegacao de formulario"
        verbose_name_plural = "Delegacoes de formularios"

    def __str__(self) -> str:
        return f"Delegacao para {self.user_id} na visita {self.visit_id}"
