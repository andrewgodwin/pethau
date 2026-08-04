from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DeleteView, DetailView, FormView, ListView, UpdateView

from assets.forms import CreateAssetForm, EditAssetForm
from assets.models import Asset, AssetHistory


class AssetCreateView(FormView):
    """
    Create a new asset and its initial history entry.
    """

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
    paginate_by = 100

    def get_queryset(self):
        queryset = Asset.objects.filter(deleted__isnull=True).order_by("tag")
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(tag__icontains=query) | Q(name__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        return context


class AssetDetailView(DetailView):
    model = Asset
    template_name = "asset_detail.html"
    context_object_name = "asset"


class AssetUpdateView(UpdateView):
    model = Asset
    form_class = EditAssetForm
    template_name = "asset_edit.html"


class AssetDeleteView(DeleteView):
    """
    Soft-deletes an asset by setting its `deleted` timestamp rather than removing the
    row from the database.
    """

    model = Asset
    template_name = "asset_confirm_delete.html"
    success_url = reverse_lazy("asset-list")

    def form_valid(self, form):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.deleted = timezone.now()
        self.object.save(update_fields=["deleted"])
        return HttpResponseRedirect(success_url)
