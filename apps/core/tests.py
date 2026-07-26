from django.test import TestCase

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
