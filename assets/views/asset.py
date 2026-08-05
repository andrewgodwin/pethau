from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from assets.forms import AssetAuditForm, CreateAssetForm, EditAssetForm
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
        form.save_image(asset)
        history = AssetHistory.objects.create(
            asset=asset,
            status="active",
            notes="Asset created",
        )
        asset.current_history = history
        asset.save(update_fields=["current_history"])
        return super().form_valid(form)


class AssetListView(ListView):
    model = Asset
    template_name = "asset_list.html"
    context_object_name = "assets"
    paginate_by = 100

    def get_queryset(self):
        queryset = (
            Asset.objects.filter(deleted__isnull=True)
            .select_related("current_history", "image")
            .order_by("tag")
        )
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

    def form_valid(self, form):
        response = super().form_valid(form)
        form.save_image(self.object)
        return response


class AssetAuditView(CreateView):
    """
    Records a new AssetHistory entry for an asset and makes it current.
    """

    model = AssetHistory
    form_class = AssetAuditForm
    template_name = "asset_audit.html"

    def dispatch(self, request, *args, **kwargs):
        self.asset = get_object_or_404(Asset, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        current = self.asset.current_history
        if current:
            initial["status"] = current.status
            initial["location"] = current.location
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["asset"] = self.asset
        return kwargs

    def form_valid(self, form):
        form.instance.asset = self.asset
        response = super().form_valid(form)
        self.asset.current_history = self.object
        self.asset.save(update_fields=["current_history"])
        return response

    def get_success_url(self):
        return self.asset.urls.view

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["asset"] = self.asset
        current = self.asset.current_history
        context["current_location"] = current.location if current else None
        return context


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


class AssetSearchView(ListView):
    """
    HTMX partial: returns a filtered, capped list of assets for the search-as-you-type
    combo box on the audit form's location field.
    """

    model = Asset
    template_name = "asset/_search_options.html"
    context_object_name = "assets"

    def get_queryset(self):
        queryset = Asset.objects.filter(deleted__isnull=True).order_by("tag")
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(tag__icontains=query) | Q(name__icontains=query)
            )
        exclude_pk = self.request.GET.get("exclude", "")
        if exclude_pk.isdigit():
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset[:20]
