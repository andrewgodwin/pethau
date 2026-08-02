from django.contrib import admin

from .models import Asset, AssetHistory, Attachment, Image, Model


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ["title", "image", "created"]
    search_fields = ["title"]


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ["title", "file", "created"]
    search_fields = ["title"]


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    list_display = ["name", "manufacturer", "short_name", "created"]
    list_filter = ["manufacturer"]
    search_fields = ["name", "manufacturer", "short_name"]
    filter_horizontal = ["images", "attachments"]


class AssetHistoryInline(admin.TabularInline):
    model = AssetHistory
    extra = 0
    filter_horizontal = ["images", "attachments"]
    ordering = ["-when"]


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["tag", "name", "model", "serial", "created"]
    list_filter = ["model"]
    search_fields = ["tag", "name", "serial", "description"]
    filter_horizontal = ["images", "attachments"]
    inlines = [AssetHistoryInline]
