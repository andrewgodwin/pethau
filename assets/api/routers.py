from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import PageNumberPagination, paginate

from api.permissions import require_permission
from assets.api.schemas import AssetOut
from assets.models import Asset

router = Router(tags=["assets"])

ASSET_QUERYSET = (
    Asset.objects.filter(deleted__isnull=True)
    .select_related(
        "model",
        "model__image",
        "owner",
        "current_history",
        "current_history__location",
        "image",
    )
    .prefetch_related("identifiers")
)


@router.get("/", response=list[AssetOut])
@paginate(PageNumberPagination, page_size=100)
def list_assets(request, q: str = ""):
    require_permission(request, "assets.view_asset")
    queryset = ASSET_QUERYSET.order_by("tag")
    q = q.strip()
    if q:
        queryset = queryset.filter(Q(tag__icontains=q) | Q(name__icontains=q))
    return queryset


@router.get("/search/", response=list[AssetOut])
def search_assets(request, q: str = "", exclude: int | None = None):
    require_permission(request, "assets.view_asset")
    queryset = ASSET_QUERYSET.order_by("tag")
    q = q.strip()
    if q:
        filters = Q(name__icontains=q)
        filters |= Q(tag__iendswith=q) if q.isdigit() else Q(tag__icontains=q)
        queryset = queryset.filter(filters)
    if exclude is not None:
        queryset = queryset.exclude(pk=exclude)
    return queryset[:20]


@router.get("/by-tag/{tag}/", response=AssetOut)
def get_asset_by_tag(request, tag: str):
    require_permission(request, "assets.view_asset")
    match = Asset.find_by_tag(tag)
    if match is None:
        raise Http404
    return get_object_or_404(ASSET_QUERYSET, pk=match.pk)


@router.get("/{int:asset_id}/", response=AssetOut)
def get_asset(request, asset_id: int):
    require_permission(request, "assets.view_asset")
    return get_object_or_404(ASSET_QUERYSET, pk=asset_id)
