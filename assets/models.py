from typing import ClassVar

import urlman
from django.conf import settings
from django.db import models
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit


class Image(models.Model):
    """A general image - referenced by other models."""

    image = models.ImageField(upload_to="asset_images/")
    title = models.CharField(max_length=255, blank=True, null=True)

    thumbnail_128 = ImageSpecField(
        source="image",
        processors=[ResizeToFit(128, 128)],
        format="JPEG",
        options={"quality": 80},
    )
    thumbnail_512 = ImageSpecField(
        source="image",
        processors=[ResizeToFit(512, 512)],
        format="JPEG",
        options={"quality": 90},
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or self.image.name


class Attachment(models.Model):
    """A file attachment such as a manual."""

    file = models.FileField(upload_to="asset_attachments/")
    title = models.CharField(max_length=255, blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or self.file.name


class Model(models.Model):
    """A model that an asset can be."""

    name = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    short_name = models.CharField(max_length=255, blank=True, null=True)

    images = models.ManyToManyField(Image, blank=True, related_name="models")
    attachments = models.ManyToManyField(Attachment, blank=True, related_name="models")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class urls(urlman.Urls):
        list = "/models/"
        view = "/models/{self.id}/"
        edit = "{view}edit/"
        delete = "{view}delete/"

    def get_absolute_url(self):
        return self.urls.view

    def display_name(self):
        if self.short_name:
            return self.short_name
        if self.manufacturer:
            return f"{self.manufacturer} {self.name}"
        return self.name

    def __str__(self):
        return self.display_name()


class Owner(models.Model):
    """An owner of an asset."""

    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Asset(models.Model):
    """A thing, with a unique identifier."""

    tag = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    images = models.ManyToManyField(Image, blank=True, related_name="assets")
    attachments = models.ManyToManyField(Attachment, blank=True, related_name="assets")

    owner = models.ForeignKey(
        Owner,
        on_delete=models.PROTECT,
        related_name="assets",
    )

    current_history = models.ForeignKey(
        "AssetHistory",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="current_link",
    )

    model = models.ForeignKey(Model, on_delete=models.PROTECT, related_name="assets")
    serial = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class urls(urlman.Urls):
        list = "/assets/"
        view = "/assets/{self.id}/"
        edit = "{view}edit/"
        delete = "{view}delete/"

    def __str__(self):
        if self.name:
            return f"{self.tag} ({self.name})"
        return self.tag

    def get_absolute_url(self):
        return self.urls.view

    @classmethod
    def next_tag(cls) -> str:
        prefix = settings.ASSET_TAG_PREFIX
        # Get highest tag (lexical sort should be fine)
        highest_tag = cls.objects.order_by("-tag").first()
        if highest_tag and highest_tag.tag.startswith(prefix):
            highest_number = int(highest_tag.tag[len(prefix) :])
        else:
            highest_number = 0
        for i in range(100):
            new_tag = f"{prefix}{str(highest_number + i + 1).zfill(5)}"
            if not cls.objects.filter(tag=new_tag).exists():
                return new_tag
        raise ValueError("Failed to generate unique tag")


class AssetHistory(models.Model):
    """Tracks an asset's current checked-in/out status as well as audits"""

    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("missing", "Missing"),
        ("destroyed", "Destroyed"),
        ("needs_repair", "Needs Repair"),
        ("archived", "Archived"),
        ("active", "Active"),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="histories")
    when = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=255, blank=True, null=True, choices=STATUS_CHOICES)
    location = models.CharField(max_length=255, blank=True, null=True)

    images = models.ManyToManyField(Image, blank=True, related_name="asset_histories")
    attachments = models.ManyToManyField(Attachment, blank=True, related_name="asset_histories")
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Asset History"
        verbose_name_plural = "Asset Histories"

    def __str__(self):
        return f"{self.asset} @ {self.when:%Y-%m-%d %H:%M}"
