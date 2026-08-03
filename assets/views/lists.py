from django.views.generic import ListView

from assets.models import Asset


class AssetListView(ListView):
    model = Asset
    template_name = "asset_list.html"
