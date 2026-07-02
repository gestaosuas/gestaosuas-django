from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    requires_system_checks = []

    def handle(self, *args, **options):
        c = connection.cursor()
        c.execute("SELECT data->>'_setor' as s, COUNT(*) FROM public.submissions GROUP BY s ORDER BY s")
        self.stdout.write("Submissions by setor:")
        for r in c.fetchall():
            s = r[0] or "(empty)"
            self.stdout.write(f"  {s}: {r[1]}")

        # Check specialized tables
        tables = [
            "cras_reports", "beneficios_reports", "naica_reports",
            "sine_reports", "qualificacao_reports", "creas_idoso_reports",
            "creas_pcd_reports", "creas_pop_rua_reports"
        ]
        self.stdout.write("\nSpecialized tables:")
        for t in tables:
            c.execute(f'SELECT COUNT(*) FROM public."{t}"')
            self.stdout.write(f"  {t}: {c.fetchone()[0]}")
