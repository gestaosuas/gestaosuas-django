from django.core.management.base import BaseCommand
from django.db import connection
import json
import uuid
from datetime import datetime

from apps.directorates.models import Directorate
from apps.cras.models import CrasReport
from apps.naica.models import NaicaReport
from apps.beneficios.models import BeneficiosReport
from apps.creasidoso.models import CreasIdosoReport, CreasPcdReport

SETOR_CONFIG = {
    "cras": {"model": CrasReport, "multi": True, "table": "cras_reports"},
    "naica": {"model": NaicaReport, "multi": True, "table": "naica_reports"},
    "creas": {"models": {"idoso": CreasIdosoReport, "deficiente": CreasPcdReport}, "multi": False, "table": None},
    "beneficios": {"model": BeneficiosReport, "multi": False, "table": "beneficios_reports"},
}

class Command(BaseCommand):
    requires_system_checks = []
    help = "Migrate submissions data to specialized tables using Django ORM"

    def handle(self, *args, **options):
        c = connection.cursor()
        
        # Get valid user UUID
        c.execute("SELECT id FROM auth.users ORDER BY random() LIMIT 1")
        row = c.fetchone()
        fb_user = row[0] if row else uuid.uuid4()
        now = datetime.now()
        
        c.execute("""
            SELECT id, directorate_id, month, year, data
            FROM public.submissions
            WHERE data->>'_setor' IN ('cras', 'naica', 'creas', 'beneficios')
            ORDER BY directorate_id, year, month
        """)
        rows = c.fetchall()
        self.stdout.write(f"Submissions: {len(rows)}\n")
        
        counts = {}
        
        for sid, dir_id, month, year, data_str in rows:
            data = json.loads(data_str) if isinstance(data_str, str) else data_str
            setor = (data.get("_setor") or "").strip()
            subcat = data.get("_subcategory", "")
            units = data.get("units", {})
            
            try:
                directorate = Directorate.objects.get(pk=dir_id)
            except Directorate.DoesNotExist:
                continue
            
            if setor == "creas":
                self._migrate_creas(dir_id, month, year, data, subcat, fb_user, now, counts)
            elif setor == "beneficios":
                self._migrate_flat(BeneficiosReport, dir_id, month, year, data, fb_user, now, counts)
            elif setor in ("cras", "naica"):
                Model = CrasReport if setor == "cras" else NaicaReport
                for unit_name, unit_data in units.items():
                    if not unit_name or not isinstance(unit_data, dict):
                        continue
                    self._migrate_multi(Model, dir_id, month, year, unit_name, unit_data, fb_user, now, counts)
        
        connection.commit()
        self.stdout.write(f"\nDone:")
        for t, n in sorted(counts.items()):
            self.stdout.write(f"  {t}: {n} records")
        
        # Show final counts
        c.execute("SELECT COUNT(*) FROM public.cras_reports")
        self.stdout.write(f"\nFinal cras_reports: {c.fetchone()[0]}")
        c.execute("SELECT COUNT(*) FROM public.naica_reports")
        self.stdout.write(f"Final naica_reports: {c.fetchone()[0]}")
        c.execute("SELECT COUNT(*) FROM public.beneficios_reports")
        self.stdout.write(f"Final beneficios_reports: {c.fetchone()[0]}")
        c.execute("SELECT COUNT(*) FROM public.creas_idoso_reports")
        self.stdout.write(f"Final creas_idoso_reports: {c.fetchone()[0]}")
        c.execute("SELECT COUNT(*) FROM public.creas_pcd_reports")
        self.stdout.write(f"Final creas_pcd_reports: {c.fetchone()[0]}")
    
    def _migrate_multi(self, Model, dir_id, month, year, unit_name, unit_data, fb_user, now, counts):
        table = Model._meta.db_table
        try:
            existing = Model.objects.filter(directorate_id=dir_id, unit_name=unit_name, month=month, year=year)
            obj = existing.first()
            if not obj:
                obj = Model(directorate_id=dir_id, unit_name=unit_name, month=month, year=year)
            
            for k, v in unit_data.items():
                if k.startswith("_") or k.endswith("_f") or k.endswith("_m"):
                    continue
                if hasattr(obj, k):
                    setattr(obj, k, int(v or 0))
            
            if not getattr(obj, "created_at", None):
                obj.created_at = now
            obj.updated_at = now
            
            if hasattr(obj, "user_id") and not getattr(obj, "user_id", None):
                obj.user_id = fb_user
            if hasattr(obj, "created_by") and not getattr(obj, "created_by", None):
                obj.created_by = str(fb_user)
            if hasattr(obj, "user_external_id") and not getattr(obj, "user_external_id", None):
                obj.user_external_id = fb_user
            
            obj.save()
            counts[table] = counts.get(table, 0) + 1
            self.stdout.write(f"  OK: {table} {unit_name} {month}/{year}")
        except Exception as e:
            self.stderr.write(f"  ERR: {table} {unit_name} {month}/{year}: {e}")
    
    def _migrate_creas(self, dir_id, month, year, data, subcat, fb_user, now, counts):
        Model = CreasPcdReport if subcat == "deficiente" else CreasIdosoReport
        table = Model._meta.db_table
        try:
            existing = Model.objects.filter(directorate_id=dir_id, month=month, year=year)
            obj = existing.first()
            if not obj:
                obj = Model(directorate_id=dir_id, month=month, year=year)
            
            for k, v in data.items():
                if k.startswith("_") or k.endswith("_f") or k.endswith("_m"):
                    continue
                if k.startswith("fa_") or k.startswith("ia_") or k.startswith("pcd_"):
                    continue
                if subcat == "deficiente" and not k.startswith("def_"):
                    continue
                if subcat == "idoso" and k.startswith("def_"):
                    continue
                if hasattr(obj, k):
                    setattr(obj, k, int(v or 0))
            
            if not getattr(obj, "created_at", None):
                obj.created_at = now
            obj.updated_at = now
            
            if not getattr(obj, "created_by", None):
                obj.created_by = fb_user
            
            obj.save()
            counts[table] = counts.get(table, 0) + 1
            self.stdout.write(f"  OK: {table} {month}/{year}")
        except Exception as e:
            self.stderr.write(f"  ERR: {table} {month}/{year}: {e}")
    
    def _migrate_flat(self, Model, dir_id, month, year, data, fb_user, now, counts):
        table = Model._meta.db_table
        try:
            existing = Model.objects.filter(directorate_id=dir_id, month=month, year=year)
            obj = existing.first()
            if not obj:
                obj = Model(directorate_id=dir_id, month=month, year=year)
            
            for k, v in data.items():
                if k.startswith("_"):
                    continue
                if hasattr(obj, k):
                    setattr(obj, k, int(v or 0))
            
            if not getattr(obj, "created_at", None):
                obj.created_at = now
            obj.updated_at = now
            
            if hasattr(obj, "user_external_id") and not getattr(obj, "user_external_id", None):
                obj.user_external_id = fb_user
            if hasattr(obj, "user_id") and not getattr(obj, "user_id", None):
                obj.user_id = fb_user
            
            obj.save()
            counts[table] = counts.get(table, 0) + 1
            self.stdout.write(f"  OK: {table} {month}/{year}")
        except Exception as e:
            self.stderr.write(f"  ERR: {table} {month}/{year}: {e}")
