import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.cras.models import CrasReport
from django.db import connections

def check_data():
    count = CrasReport.objects.count()
    print(f"Total CrasReport: {count}")
    
    years = CrasReport.objects.values_list('year', flat=True).distinct()
    print(f"Years: {list(years)}")
    
    if count > 0:
        first = CrasReport.objects.first()
        print(f"First report: {first.unit_name}, {first.month}/{first.year}")

if __name__ == "__main__":
    check_data()
