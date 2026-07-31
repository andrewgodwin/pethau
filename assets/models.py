from typing import ClassVar

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


class Attachment(models.Model):
    """A file attachment such as a manual."""

    file = models.FileField(upload_to="asset_attachments/")
    title = models.CharField(max_length=255, blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class Model(models.Model):
    """A model that an asset can be."""

    name = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)

    images = models.ManyToManyField(Image, blank=True, related_name="models")
    attachments = models.ManyToManyField(Attachment, blank=True, related_name="models")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class Asset(models.Model):
    """A thing, with a unique identifier."""

    tag = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    images = models.ManyToManyField(Image, blank=True, related_name="assets")
    attachments = models.ManyToManyField(Attachment, blank=True, related_name="assets")

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

    status = models.CharField(
        max_length=255, blank=True, null=True, choices=STATUS_CHOICES
    )
    location = models.CharField(max_length=255, blank=True, null=True)

    images = models.ManyToManyField(Image, blank=True, related_name="asset_histories")
    attachments = models.ManyToManyField(
        Attachment, blank=True, related_name="asset_histories"
    )
    notes = models.TextField(blank=True, null=True)
