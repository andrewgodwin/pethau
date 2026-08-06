from datetime import datetime

from ninja import Schema


class ImageOut(Schema):
    id: int
    title: str | None
    url: str
    thumbnail_128: str
    thumbnail_512: str

    @staticmethod
    def resolve_url(obj):
        return obj.image.url

    @staticmethod
    def resolve_thumbnail_128(obj):
        return obj.thumbnail_128.url

    @staticmethod
    def resolve_thumbnail_512(obj):
        return obj.thumbnail_512.url


class OwnerOut(Schema):
    id: int
    name: str
    notes: str | None


class AssetIdentifierOut(Schema):
    id: int
    kind: str
    kind_display: str
    value: str

    @staticmethod
    def resolve_kind_display(obj):
        return obj.get_kind_display()


class AssetHistoryOut(Schema):
    id: int
    when: datetime
    status: str | None
    status_display: str | None
    status_color: str
    location_id: int | None
    location_tag: str | None
    notes: str | None

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display() if obj.status else None

    @staticmethod
    def resolve_location_tag(obj):
        return obj.location.tag if obj.location_id else None


class ModelOut(Schema):
    """
    An asset's model/type -- this is the "embedded model details" payload.
    """

    id: int
    name: str
    manufacturer: str | None
    short_name: str | None
    display_name: str
    image: ImageOut | None

    @staticmethod
    def resolve_display_name(obj):
        return obj.display_name()


class AssetOut(Schema):
    id: int
    tag: str
    name: str | None
    description: str | None
    serial: str | None
    notes: str | None
    category: str | None
    category_display: str | None
    owner: OwnerOut
    model: ModelOut
    image: ImageOut | None
    current_history: AssetHistoryOut | None
    identifiers: list[AssetIdentifierOut]
    created: datetime
    updated: datetime

    @staticmethod
    def resolve_category_display(obj):
        return obj.get_category_display() if obj.category else None

    @staticmethod
    def resolve_identifiers(obj):
        return obj.identifiers.all()
