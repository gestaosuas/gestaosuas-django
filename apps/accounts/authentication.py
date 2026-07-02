import json
import urllib.request
import urllib.error

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

from .models import Profile


User = get_user_model()


class SupabaseAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        if not username or not password:
            return None

        supabase_url = settings.SUPABASE_URL
        anon_key = settings.SUPABASE_ANON_KEY

        if not supabase_url:
            return None

        url = f"{supabase_url}/auth/v1/token?grant_type=password"

        payload = json.dumps({"email": username, "password": password}).encode()
        headers = {
            "Content-Type": "application/json",
            "apikey": anon_key,
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return None
        except urllib.error.URLError:
            return None

        supabase_user = body.get("user") or body.get("user_id") or {}
        supabase_id = supabase_user.get("id")
        email = supabase_user.get("email", username)

        if not supabase_id:
            return None

        user, created = User.objects.get_or_create(
            id=supabase_id,
            defaults={"username": email, "email": email},
        )

        user.set_unusable_password()
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        if not profile.full_name:
            profile.full_name = supabase_user.get("user_metadata", {}).get("full_name", email)
            profile.save()

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
