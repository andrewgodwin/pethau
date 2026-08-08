from django import forms
from django.urls import reverse

from assets.labels import TEMPLATES, template_choices
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
                required=False, label="Remove image"
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

    The status/location fields are not on Asset itself; they're used to populate the
    asset's initial AssetHistory entry.
    """

    status = forms.ChoiceField(choices=AssetHistory.STATUS_CHOICES, initial="active")
    location = forms.ModelChoiceField(
        queryset=Asset.objects.filter(deleted__isnull=True).order_by("tag"),
        required=False,
        widget=forms.HiddenInput,
    )

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
        self.fields["model"].widget = forms.HiddenInput()
        self.fields["owner"].queryset = Owner.objects.order_by("name")
        self.fields["tag"].widget.attrs.update({"autofocus": True})
        if not self.is_bound and not self.instance.pk:
            self.fields["tag"].initial = Asset.next_tag()
            default_owner = Owner.objects.filter(default=True).first()
            if default_owner:
                self.fields["owner"].initial = default_owner

    @property
    def selected_location(self):
        """
        The asset currently chosen as the location, so the combo box can re-display it
        after a failed submission.
        """
        value = self["location"].value()
        if not value or not str(value).isdigit():
            return None
        return self.fields["location"].queryset.filter(pk=value).first()


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
        self.fields["model"].widget = forms.HiddenInput()
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
        self.fields["location"].widget = forms.HiddenInput()


class BulkAuditLocationForm(forms.Form):
    """
    Form for picking the location to bulk-audit against.
    """

    location = forms.ModelChoiceField(
        queryset=Asset.objects.filter(deleted__isnull=True).order_by("tag"),
        widget=forms.HiddenInput,
    )


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


class TemplateSelect(forms.Select):
    """
    A template picker that tags each option with the template's format and whether it
    takes a sheet offset, so the page can show or hide fields to match.
    """

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        template = TEMPLATES.get(str(value))
        if template:
            option["attrs"]["data-format"] = template.format
            option["attrs"]["data-supports-offset"] = (
                "1" if template.supports_offset else "0"
            )
        return option


class LabelPrintForm(forms.Form):
    """
    Form for the label printing page: which assets, which template, and how many labels
    to skip on a part-used sheet.
    """

    spec = forms.CharField(
        label="Assets",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "autofocus": True, "autocomplete": "off"}
        ),
        help_text="Tags separated by commas or spaces. Use 123-125 for a range and 345x2 (or 345#2) for copies.",
    )
    template = forms.ChoiceField(
        label="Template", choices=template_choices, widget=TemplateSelect
    )
    offset = forms.IntegerField(
        label="Skip labels",
        required=False,
        min_value=0,
        max_value=999,
        help_text="Leave this many labels blank at the start, to reuse a part-used sheet.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Every field re-resolves the preview as it changes
        for name, field in self.fields.items():
            field.widget.attrs.update(
                {
                    "hx-get": reverse("label-resolve"),
                    "hx-target": "#label-resolve",
                    "hx-include": "closest form",
                    "hx-trigger": (
                        "input changed delay:400ms" if name == "spec" else "change"
                    ),
                }
            )
