from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from assets.forms import CreateAssetForm
from assets.models import Asset, AssetHistory


class AssetCreateView(FormView):
    """Create a new asset and its initial history entry."""

    template_name = "asset_create.html"
    form_class = CreateAssetForm
    success_url = reverse_lazy("asset-list")

    def form_valid(self, form):
        asset = form.save()
        AssetHistory.objects.create(
            asset=asset,
            status="active",
            notes="Asset created",
        )
        return super().form_valid(form)


class AssetListView(ListView):
    model = Asset
    template_name = "asset_list.html"
    context_object_name = "assets"


class AssetDetailView(DetailView):
    model = Asset
    template_name = "asset_detail.html"
    context_object_name = "asset"
