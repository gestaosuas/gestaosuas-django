from django import forms
from apps.core.forms import StyledMonitoringForm


class GenericMonitoringForm(StyledMonitoringForm):
    # Este formulário será preenchido dinamicamente na view
    # Mas herdamos do StyledMonitoringForm para manter o visual premium
    
    month = forms.ChoiceField(
        choices=[(i, str(i)) for i in range(1, 13)],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    year = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": "form-input", "min": 2020})
    )

    def __init__(self, *args, **kwargs):
        form_definition = kwargs.pop("form_definition", None)
        super().__init__(*args, **kwargs)
        
        if form_definition and isinstance(form_definition, list):
            for section in form_definition:
                fields = section.get("fields", [])
                for field in fields:
                    name = field.get("name")
                    label = field.get("label", name)
                    field_type = field.get("type", "number")
                    
                    if field_type == "number":
                        self.fields[name] = forms.IntegerField(
                            label=label,
                            required=False,
                            initial=0,
                            widget=forms.NumberInput(attrs={"class": "form-input"})
                        )
                    elif field_type == "text":
                        self.fields[name] = forms.CharField(
                            label=label,
                            required=False,
                            widget=forms.TextInput(attrs={"class": "form-input"})
                        )
                    elif field_type == "textarea":
                        self.fields[name] = forms.CharField(
                            label=label,
                            required=False,
                            widget=forms.Textarea(attrs={"class": "form-input", "rows": 3})
                        )
