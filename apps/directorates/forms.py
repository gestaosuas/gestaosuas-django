from django import forms
from .models import Osc, Visit, WorkPlan

class OscForm(forms.ModelForm):
    subsidized_type = forms.ChoiceField(
        choices=[('number', 'Número'), ('demand', 'Conforme Demanda')],
        widget=forms.RadioSelect,
        initial='number'
    )

    class Meta:
        model = Osc
        fields = [
            'name', 'activity_type', 'cep', 'address', 
            'number', 'neighborhood', 'phone', 'subsidized_count'
        ]
        widgets = {
            'activity_type': forms.Select(choices=[]), # Will be populated in __init__
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate activity types from Next.js list
        activity_types = [
            "Serviço de Convivência e Fortalecimento de Vínculos – 6 a 15 anos",
            "Serviço de Promoção da Integração ao Mundo Trabalho",
            "Fortalecimento do trabalho com famílias em situação de vulnerabilidade",
            "Trabalho com famílias e gestantes em situação de vulnerabilidade social",
            "Assessoria",
            "Serviço Especializado para População em Situação de Rua",
            "Serviço de Habilitação e Reabilitação da Pessoa com Deficiência",
            "Serviço Acolhimento Residência Inclusiva",
            "Serviço de Acolhimento Institucional para Idoso",
            "Serviço de Acolhimento Institucional para Crianças e Adolescentes",
            "Serviço de Família Acolhedora para Crianças e Adolescentes e Apadrinhamento Afetivo",
            "Serviço de Defesa de Direitos da Criança e Adolescente/ Família",
            "Serviço de Atendimento Especializado à Mulher Vítima de Violência",
            "Serviço de Acolhimento Institucional para Mulher Vítima de Violência"
        ]
        self.fields['activity_type'].widget.choices = [(t, t) for t in activity_types]
        
        if self.instance and self.instance.subsidized_count == -1:
            self.fields['subsidized_type'].initial = 'demand'

    def clean(self):
        cleaned_data = super().clean()
        subsidized_type = cleaned_data.get('subsidized_type')
        if subsidized_type == 'demand':
            cleaned_data['subsidized_count'] = -1
        return cleaned_data

class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['osc', 'visit_date', 'visit_time', 'status']
        widgets = {
            'visit_date': forms.DateInput(attrs={'type': 'date'}),
            'visit_time': forms.TimeInput(attrs={'type': 'time'}),
        }
