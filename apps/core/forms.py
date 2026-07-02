from django import forms
from apps.core.utils import MONTH_LABELS as MONTH_CHOICES


class StyledMonitoringForm(forms.ModelForm):
    month = forms.ChoiceField(
        label="Mes", choices=MONTH_CHOICES,
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    base_labels = {"month": "Mes", "year": "Ano"}
    labels = {}
    help_texts = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.label = self.labels.get(name, self.base_labels.get(name, field.label))
            if name in {"month", "year"}:
                field.widget.attrs["class"] = "form-input"
                continue

            attrs = {"class": "form-input", "min": 0}
            if getattr(field, "disabled", False):
                attrs["readonly"] = True
            field.widget = forms.NumberInput(attrs=attrs)
            field.required = False
            field.initial = field.initial or 0
            if name in self.help_texts:
                field.help_text = self.help_texts[name]
