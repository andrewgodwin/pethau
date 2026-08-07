from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from assets.forms import BulkAuditLocationForm
from assets.models import Asset, AssetHistory
from assets.views.mixins import LoginAndPermissionRequiredMixin

SESSION_KEY = "bulk_audit"


def _get_state(request):
    return request.session.get(SESSION_KEY, {"location_id": None, "entries": {}})


def _save_state(request, state):
    request.session[SESSION_KEY] = state
    request.session.modified = True


def _bulk_audit_context(state):
    """
    Resolves the session state into template context: the current location (if it still
    exists) and the tracking-list entries, newest-scanned first.

    Clears stale state (e.g. a since-deleted location) in place, so callers should
    persist `state` afterwards if they want that cleanup to stick.
    """
    location = None
    location_id = state.get("location_id")
    if location_id:
        location = Asset.objects.filter(pk=location_id, deleted__isnull=True).first()
        if location is None:
            state["location_id"] = None
            state["entries"] = {}

    history_ids = list(state.get("entries", {}).values())
    histories_by_id = {
        history.pk: history
        for history in AssetHistory.objects.filter(pk__in=history_ids).select_related(
            "asset", "asset__image", "location"
        )
    }
    entries = [
        histories_by_id[history_id]
        for history_id in reversed(history_ids)
        if history_id in histories_by_id
    ]

    return {
        "location": location,
        "entries": entries,
        "status_choices": AssetHistory.STATUS_CHOICES,
    }


class BulkAuditView(LoginAndPermissionRequiredMixin, View):
    """
    Main bulk-audit page.

    Lets user pick a location, then scan assets against it
    """

    permission_required = "assets.add_assethistory"

    def get(self, request):
        state = _get_state(request)
        context = _bulk_audit_context(state)
        _save_state(request, state)
        context["location_form"] = BulkAuditLocationForm(
            initial={"location": context["location"]}
        )
        return render(request, "asset/bulk_audit.html", context)


class BulkAuditSetLocationView(LoginAndPermissionRequiredMixin, View):
    """
    Sets the location for the current bulk-audit session.

    Audit page submits here, we set the location in the session, and then go back.
    """

    permission_required = "assets.add_assethistory"

    def post(self, request):
        form = BulkAuditLocationForm(request.POST)
        if form.is_valid():
            state = _get_state(request)
            state["location_id"] = form.cleaned_data["location"].pk
            # Clear every time, even if it's same location
            state["entries"] = {}
            _save_state(request, state)
        return HttpResponseRedirect(reverse("bulk-audit"))


class BulkAuditAddEntryView(LoginAndPermissionRequiredMixin, View):
    """
    Records (or updates) an AssetHistory entry for a tag.

    The record is created immediately, and then the history for this session is stored
    in the state.
    """

    permission_required = "assets.add_assethistory"

    def post(self, request):
        state = _get_state(request)
        context = _bulk_audit_context(state)
        location = context["location"]
        tag = request.POST.get("tag", "").strip()
        error = None

        if not location:
            error = "Pick a location before adding assets." if tag else None
        elif tag:
            # Try looking up tag by exact match, falling back to a unique numeric suffix
            asset = Asset.find_by_tag(tag)
            if asset is None:
                if Asset.objects.filter(tag__iexact=tag).exists():
                    error = f"Asset '{tag}' has been deleted."
                else:
                    error = f"No asset found with tag '{tag}'."
            elif asset.pk == location.pk:
                error = "Can't audit the location into itself."
            else:
                # Alright, asset is good, log it
                entries = state.setdefault("entries", {})
                asset_key = str(asset.pk)
                if asset_key in entries:
                    # Move this asset's entry to the end (top of the newest-first list)
                    # without creating a second history row for a rescan.
                    entries[asset_key] = entries.pop(asset_key)
                else:
                    # Use previous status if it exists
                    default_status = (
                        asset.current_history.status
                        if asset.current_history
                        else "active"
                    )
                    # Alright, make it
                    history = AssetHistory.objects.create(
                        asset=asset,
                        status=default_status,
                        location=location,
                        notes="",
                    )
                    asset.current_history = history
                    asset.save(update_fields=["current_history"])
                    entries[asset_key] = history.pk
                _save_state(request, state)
                context = _bulk_audit_context(state)

        context["error"] = error
        return render(request, "asset/_bulk_audit_body.html", context)


class BulkAuditEntryStatusView(LoginAndPermissionRequiredMixin, View):
    """
    Updates the status of a single entry recorded during the current bulk-audit session.
    """

    permission_required = "assets.add_assethistory"

    def post(self, request, pk):
        state = _get_state(request)
        if pk not in state.get("entries", {}).values():
            return HttpResponseNotFound()

        status = request.POST.get("status", "")
        if status in dict(AssetHistory.STATUS_CHOICES):
            AssetHistory.objects.filter(pk=pk).update(status=status)

        context = _bulk_audit_context(state)
        return render(request, "asset/_bulk_audit_body.html", context)


class BulkAuditEntryUndoView(LoginAndPermissionRequiredMixin, View):
    """
    Undoes a mis-scanned entry from the current bulk-audit session: deletes the
    AssetHistory row it created, and recalculates the asset's current_history from
    whatever history remains.
    """

    permission_required = "assets.add_assethistory"

    def post(self, request, pk):
        state = _get_state(request)
        entries = state.get("entries", {})
        if pk not in entries.values():
            return HttpResponseNotFound()

        history = AssetHistory.objects.filter(pk=pk).select_related("asset").first()
        if history is not None:
            asset = history.asset
            history.delete()
            asset.current_history = asset.histories.order_by("-when", "-pk").first()
            asset.save(update_fields=["current_history"])
            entries.pop(str(asset.pk), None)
            _save_state(request, state)

        context = _bulk_audit_context(state)
        return render(request, "asset/_bulk_audit_body.html", context)
