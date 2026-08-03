from django import forms

from assets.models import Asset, Model


class AssetForm(forms.ModelForm):
    """Form for creating a new asset."""

    class Meta:
        model = Asset
        fields = ["tag", "name", "model", "serial", "description", "notes"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["model"].queryset = Model.objects.order_by("manufacturer", "name")
        self.fields["tag"].widget.attrs.update({"autofocus": True})
