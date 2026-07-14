from apps.directorates.models import Directorate
from apps.accounts.mixins import user_has_directorate_access
from django.db import OperationalError, ProgrammingError

def directorates_processor(request):
    try:
        all_dirs = list(Directorate.objects.order_by("name"))

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            all_dirs = [d for d in all_dirs if user_has_directorate_access(user, d)]
        else:
            all_dirs = []

        main_names = [
            'Benefícios Socioassistenciais', 
            'Qualificação Profissional e SINE', 
            'CRAS', 
            'CEAI', 
            'CREAS Idoso e Pessoa com Deficiência', 
            'População de Rua e Migrantes', 
            'NAICAs', 
            'Proteção Especial à Criança e Adolescente', 
            'Casa da Mulher'
        ]

        
        main_directorates = []
        monitoring_directorates = []
        outros_directorates = []
        
        for d in all_dirs:
            name_lower = d.name.lower()
            if d.name in main_names:
                main_directorates.append(d)
            elif 'outros' in name_lower:
                outros_directorates.append(d)
            else:
                monitoring_directorates.append(d)
                
        # Sort main directorates according to the order in main_names
        main_directorates.sort(key=lambda x: main_names.index(x.name) if x.name in main_names else 999)
        
        return {
            "main_directorates": main_directorates,
            "monitoring_directorates": monitoring_directorates,
            "outros_directorates": outros_directorates,
        }
    except (OperationalError, ProgrammingError, AttributeError):
        return {
            "main_directorates": all_dirs if 'all_dirs' in locals() else [],
            "monitoring_directorates": [],
            "outros_directorates": [],
        }
