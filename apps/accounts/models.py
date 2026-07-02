import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

class Profile(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_DIRECTOR = "diretor"
    ROLE_AGENTE = "agente"
    ROLE_USER = "user"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Administrador"),
        (ROLE_DIRECTOR, "Diretor"),
        (ROLE_AGENTE, "Agente"),
        (ROLE_USER, "Usuario"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile", db_column="id", primary_key=True)
    full_name = models.TextField(blank=True)
    role = models.TextField(choices=ROLE_CHOICES, default=ROLE_USER)
    created_at = models.DateTimeField(null=True, blank=True)
    primary_directorate = models.ForeignKey(
        "directorates.Directorate",
        on_delete=models.DO_NOTHING,
        db_column="directorate_id",
        null=True,
        blank=True,
        related_name="primary_profiles",
    )
    directorates = models.ManyToManyField(
        "directorates.Directorate",
        through="accounts.ProfileDirectorate",
        related_name="profiles",
    )

    class Meta:
        db_table = "profiles"
        managed = False
        ordering = ["full_name"]

    def __str__(self) -> str:
        return self.full_name or self.user.get_username()


class ProfileDirectorate(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.DO_NOTHING, db_column="profile_id", primary_key=True)
    directorate = models.ForeignKey("directorates.Directorate", on_delete=models.DO_NOTHING, db_column="directorate_id")
    assigned_at = models.DateTimeField(auto_now_add=True)
    allowed_units = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "profile_directorates"
        managed = False
        unique_together = ("profile", "directorate")
        verbose_name = "Vinculo perfil-diretoria"
        verbose_name_plural = "Vinculos perfil-diretoria"

    def __str__(self) -> str:
        return f"{self.profile} -> {self.directorate}"
