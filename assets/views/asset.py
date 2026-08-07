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
from assets.views.mixins import LoginAndPermissionRequiredMixin


class AssetCreateView(LoginAndPermissionRequiredMixin, FormView):
    """
    Create a new asset and its initial history entry.
    """

    permission_required = "assets.add_asset"
    template_name = "asset/create.html"
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

    def get_success_url(self):
        if "_addanother" in self.request.POST:
            return reverse_lazy("asset-create")
        return super().get_success_url()


class AssetListView(LoginAndPermissionRequiredMixin, ListView):
    permission_required = "assets.view_asset"
    model = Asset
    template_name = "asset/list.html"
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


class AssetDetailView(LoginAndPermissionRequiredMixin, DetailView):
    permission_required = "assets.view_asset"
    model = Asset
    template_name = "asset/detail.html"
    context_object_name = "asset"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["histories"] = (
            self.object.histories.select_related("location")
            .prefetch_related("images")
            .order_by("-when")
        )
        return context


class AssetUpdateView(LoginAndPermissionRequiredMixin, UpdateView):
    permission_required = "assets.change_asset"
    model = Asset
    form_class = EditAssetForm
    template_name = "asset/edit.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        form.save_image(self.object)
        return response


class AssetAuditView(LoginAndPermissionRequiredMixin, CreateView):
    """
    Records a new AssetHistory entry for an asset and makes it current.
    """

    permission_required = "assets.add_assethistory"
    model = AssetHistory
    form_class = AssetAuditForm
    template_name = "asset/audit.html"

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


class AssetDeleteView(LoginAndPermissionRequiredMixin, DeleteView):
    """
    Soft-deletes an asset by setting its `deleted` timestamp rather than removing the
    row from the database.
    """

    permission_required = "assets.delete_asset"
    model = Asset
    template_name = "asset/confirm_delete.html"
    success_url = reverse_lazy("asset-list")

    def form_valid(self, form):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.deleted = timezone.now()
        self.object.save(update_fields=["deleted"])
        return HttpResponseRedirect(success_url)


class AssetSearchView(LoginAndPermissionRequiredMixin, ListView):
    """
    HTMX partial: returns a filtered, capped list of assets for the search-as-you-type
    combo box on the audit form's location field.
    """

    permission_required = "assets.view_asset"
    model = Asset
    template_name = "asset/_search_options.html"
    context_object_name = "assets"

    def get_queryset(self):
        queryset = Asset.objects.filter(deleted__isnull=True).order_by("tag")
        query = self.request.GET.get("q", "").strip()
        if query:
            filters = Q(name__icontains=query)
            if query.isdigit():
                # A pure number is likely a shorthand for the numeric suffix of a
                # tag (e.g. "03" for "AER00003"), so match on tag ending rather
                # than substring. Unlike find_by_tag(), this deliberately allows
                # multiple results so the dropdown can keep narrowing as more
                # digits are typed instead of going blank on ambiguity.
                filters |= Q(tag__iendswith=query)
            else:
                filters |= Q(tag__icontains=query)
            queryset = queryset.filter(filters)
        exclude_pk = self.request.GET.get("exclude", "")
        if exclude_pk.isdigit():
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset[:20]
