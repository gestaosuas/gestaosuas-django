from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    requires_system_checks = []

    def handle(self, *args, **options):
        c = connection.cursor()
        c.execute("SELECT month, atend_empregador, atend_online_empregador, atend_trabalhador, atend_online_trabalhador FROM public.sine_reports ORDER BY month")
        rows = c.fetchall()
        self.stdout.write(f"Sine data ({len(rows)} rows):")
        for r in rows:
            self.stdout.write(f"  month={r[0]}: emp={r[1]}, emp_online={r[2]}, trab={r[3]}, trab_online={r[4]}")
        
        from apps.sinecp.views import SINE_CARD_FIELDS
        self.stdout.write(f"\nSINE_CARD_FIELDS: {[(l, f) for l, f, i, c in SINE_CARD_FIELDS]}")
