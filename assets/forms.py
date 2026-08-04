from django import forms

from assets.models import Asset, Model, Owner


class CreateAssetForm(forms.ModelForm):
    """Form for creating a new asset."""

    class Meta:
        model = Asset
        fields = ["tag", "owner", "model", "name", "description", "notes", "serial"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["model"].queryset = Model.objects.order_by("manufacturer", "name")
        self.fields["owner"].queryset = Owner.objects.order_by("name")
        self.fields["tag"].widget.attrs.update({"autofocus": True})
        if not self.is_bound and not self.instance.pk:
            self.fields["tag"].initial = Asset.next_tag()


class ModelForm(forms.ModelForm):
    """Form for creating/editing a model."""

    class Meta:
        model = Model
        fields = ["name", "manufacturer", "short_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.update({"autofocus": True})
        # Ensure empty values are treated as None (for uniqueness)
        self.fields["manufacturer"].empty_value = None
        self.fields["short_name"].empty_value = None
