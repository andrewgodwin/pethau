from django import forms

from assets.models import Asset, AssetHistory, Image, Model, Owner


class SingleImageMixin:
    """
    Adds a single optional image upload field to a ModelForm for a model with an `image`
    FK to `Image`, plus a way to remove the current image when editing an instance that
    already has one.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image_file"] = forms.ImageField(required=False, label="Image")
        if self.instance.pk and self.instance.image_id:
            self.fields["remove_image"] = forms.BooleanField(
                required=False, label="Remove current image"
            )

    def save_image(self, instance):
        uploaded = self.cleaned_data.get("image_file")
        if uploaded:
            instance.image = Image.objects.create(image=uploaded)
            instance.save(update_fields=["image"])
        elif self.cleaned_data.get("remove_image"):
            instance.image = None
            instance.save(update_fields=["image"])


class CreateAssetForm(SingleImageMixin, forms.ModelForm):
    """
    Form for creating a new asset.
    """

    class Meta:
        model = Asset
        fields = [
            "tag",
            "owner",
            "model",
            "name",
            "description",
            "notes",
            "serial",
            "category",
        ]
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


class EditAssetForm(SingleImageMixin, forms.ModelForm):
    """
    Form for editing an existing asset.
    """

    class Meta:
        model = Asset
        fields = [
            "tag",
            "owner",
            "model",
            "name",
            "description",
            "notes",
            "serial",
            "category",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["model"].queryset = Model.objects.order_by("manufacturer", "name")
        self.fields["owner"].queryset = Owner.objects.order_by("name")
        self.fields["tag"].widget.attrs.update({"autofocus": True})


class AssetAuditForm(forms.ModelForm):
    """
    Form for recording a new audit entry (status/location/notes) for an asset.
    """

    class Meta:
        model = AssetHistory
        fields = ["status", "location", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, asset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].widget.attrs.update({"autofocus": True})
        location_queryset = Asset.objects.filter(deleted__isnull=True).order_by("tag")
        if asset is not None:
            location_queryset = location_queryset.exclude(pk=asset.pk)
        self.fields["location"].queryset = location_queryset


class ModelForm(SingleImageMixin, forms.ModelForm):
    """
    Form for creating/editing a model.
    """

    class Meta:
        model = Model
        fields = ["name", "manufacturer", "short_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.update({"autofocus": True})
        # Ensure empty values are treated as None (for uniqueness)
        self.fields["manufacturer"].empty_value = None
        self.fields["short_name"].empty_value = None
