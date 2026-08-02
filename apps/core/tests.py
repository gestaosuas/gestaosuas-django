import os
import uuid

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.accounts.tests import make_user
from apps.core.utils import build_series_or_none, build_variation_or_none


class FakeReport:
    """Standin minimo pra nao precisar de um BeneficiosReport real (managed=False,
    exigiria banco) so pra testar funcoes puras que so leem um atributo por vez."""

    def __init__(self, **fields):
        for name, value in fields.items():
            setattr(self, name, value)


class BuildSeriesOrNoneTests(TestCase):
    def test_month_without_report_row_is_none(self):
        reports_by_month = {1: FakeReport(valor=10)}
        series = build_series_or_none(reports_by_month, "valor")
        self.assertEqual(series[0], 10)
        self.assertIsNone(series[1])

    def test_month_with_report_but_field_zero_is_zero_not_none(self):
        reports_by_month = {1: FakeReport(valor=0)}
        series = build_series_or_none(reports_by_month, "valor")
        self.assertEqual(series[0], 0)
        self.assertIsNotNone(series[0])

    def test_empty_reports_gives_all_none(self):
        series = build_series_or_none({}, "valor")
        self.assertEqual(series, [None] * 12)


class BuildVariationOrNoneTests(TestCase):
    def test_specific_month_compares_to_previous(self):
        reports_by_month = {2: FakeReport(valor=150), 3: FakeReport(valor=200)}
        result = build_variation_or_none(reports_by_month, "valor", "3")
        self.assertIsNotNone(result)
        self.assertTrue(result["is_up"])
        self.assertAlmostEqual(result["value"], 33.3, places=1)

    def test_specific_month_without_previous_report_is_none(self):
        reports_by_month = {3: FakeReport(valor=200)}
        result = build_variation_or_none(reports_by_month, "valor", "3")
        self.assertIsNone(result)

    def test_january_never_has_a_comparison(self):
        reports_by_month = {1: FakeReport(valor=50)}
        result = build_variation_or_none(reports_by_month, "valor", "1")
        self.assertIsNone(result)

    def test_all_mode_compares_last_two_consecutive_reported_months(self):
        reports_by_month = {4: FakeReport(valor=80), 5: FakeReport(valor=100)}
        result = build_variation_or_none(reports_by_month, "valor", "all")
        self.assertIsNotNone(result)
        self.assertTrue(result["is_up"])
        self.assertEqual(result["value"], 25.0)

    def test_all_mode_none_when_last_reported_month_has_no_immediate_predecessor(self):
        reports_by_month = {2: FakeReport(valor=80), 5: FakeReport(valor=100)}
        result = build_variation_or_none(reports_by_month, "valor", "all")
        self.assertIsNone(result)

    def test_all_mode_none_with_fewer_than_two_reports(self):
        reports_by_month = {5: FakeReport(valor=100)}
        result = build_variation_or_none(reports_by_month, "valor", "all")
        self.assertIsNone(result)

    def test_previous_value_zero_reports_up_100_percent(self):
        reports_by_month = {4: FakeReport(valor=0), 5: FakeReport(valor=10)}
        result = build_variation_or_none(reports_by_month, "valor", "all")
        self.assertEqual(result, {"value": 100, "is_up": True})

    def test_previous_and_current_both_zero_is_none(self):
        reports_by_month = {4: FakeReport(valor=0), 5: FakeReport(valor=0)}
        result = build_variation_or_none(reports_by_month, "valor", "all")
        self.assertIsNone(result)


class ProtectedMediaViewTests(TestCase):
    """core:protected-media substitui o /media/ direto do Django (só
    registrado com DEBUG=True — dava 404 em produção, confirmado nesta
    sessão contra a VPS real) por uma rota que exige login e valida que o
    caminho resolvido continua dentro de MEDIA_ROOT (path traversal)."""

    def setUp(self):
        self.rel_path = f"test-protected/{uuid.uuid4().hex}.txt"
        self.abs_path = os.path.join(str(settings.MEDIA_ROOT), self.rel_path)
        os.makedirs(os.path.dirname(self.abs_path), exist_ok=True)
        with open(self.abs_path, "wb") as f:
            f.write(b"conteudo de teste")

    def tearDown(self):
        if os.path.isfile(self.abs_path):
            os.remove(self.abs_path)

    def _url(self, path):
        return reverse("core:protected-media", kwargs={"file_path": path})

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self._url(self.rel_path))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_authenticated_user_downloads_existing_file(self):
        user, _ = make_user()
        self.client.force_login(user)
        response = self.client.get(self._url(self.rel_path))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"conteudo de teste")

    def test_nonexistent_file_is_404(self):
        user, _ = make_user()
        self.client.force_login(user)
        response = self.client.get(self._url("test-protected/nao-existe.txt"))
        self.assertEqual(response.status_code, 404)

    def test_path_traversal_outside_media_root_is_blocked(self):
        user, _ = make_user()
        self.client.force_login(user)
        response = self.client.get(self._url("../../config/settings.py"))
        self.assertEqual(response.status_code, 404)
