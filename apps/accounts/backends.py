from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


class LockoutModelBackend(ModelBackend):
    """ModelBackend com limite de tentativas de login por username.

    Cobre tanto o login normal (/accounts/login/) quanto o /admin/ - os dois
    passam por authenticate(), que percorre AUTHENTICATION_BACKENDS. Bloqueio
    por username (nao por IP): mais simples, e nao depende de tratar
    X-Forwarded-For atras do proxy Tailscale (nao configurado hoje). Trade-off
    aceito: alguem pode travar a propria conta tentando errar de proposito,
    mas nao a de outras pessoas.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username:
            return None
        key = f"login_attempts:{username.lower()}"
        if cache.get(key, 0) >= MAX_ATTEMPTS:
            return None
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user is None:
            cache.set(key, cache.get(key, 0) + 1, LOCKOUT_SECONDS)
        else:
            cache.delete(key)
        return user
