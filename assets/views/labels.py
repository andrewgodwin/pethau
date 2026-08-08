from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from assets.forms import LabelPrintForm
from assets.labels import DEFAULT_TEMPLATE, get_template, parse_spec
from assets.views.mixins import LoginAndPermissionRequiredMixin

SESSION_KEY = "label_print"

# Most ZPL is short, but a big batch shouldn't be dumped into the page wholesale
ZPL_PREVIEW_LIMIT = 20000


def _preferences(request):
    return request.session.get(SESSION_KEY, {})


def _save_preferences(request, template_slug, offset):
    request.session[SESSION_KEY] = {"template": template_slug, "offset": offset}
    request.session.modified = True


def _resolve(data):
    """
    Turns raw query data into the context the preview partial needs.
    """
    form = LabelPrintForm(data)
    form.is_valid()
    cleaned = form.cleaned_data if hasattr(form, "cleaned_data") else {}
    template = get_template(cleaned.get("template") or data.get("template"))
    offset = cleaned.get("offset") or 0
    spec = parse_spec(cleaned.get("spec", data.get("spec", "")))

    zpl_preview = None
    if spec.is_printable and template.format == "zpl":
        zpl_preview = template.render(spec.assets()).decode("utf-8")[:ZPL_PREVIEW_LIMIT]

    return {
        "form": form,
        "spec": spec,
        "template": template,
        "offset": offset,
        "zpl_preview": zpl_preview,
    }


class LabelPrintView(LoginAndPermissionRequiredMixin, View):
    """
    Main label printing page.

    Lets the user describe a set of assets with a compact spec, pick a template, and
    render the result as a PDF sheet or as ZPL.
    """

    permission_required = "assets.view_asset"

    def get(self, request):
        preferences = _preferences(request)
        data = {
            "spec": request.GET.get("spec", ""),
            "template": request.GET.get("template")
            or preferences.get("template")
            or DEFAULT_TEMPLATE,
            "offset": request.GET.get("offset") or preferences.get("offset") or 0,
        }
        context = _resolve(data)
        context["form"] = LabelPrintForm(initial=data)
        return render(request, "label/print.html", context)


class LabelResolveView(LoginAndPermissionRequiredMixin, View):
    """
    HTMX endpoint that re-renders the resolved preview as the form changes.
    """

    permission_required = "assets.view_asset"

    def get(self, request):
        context = _resolve(request.GET)
        _save_preferences(request, context["template"].slug, context["offset"])
        return render(request, "label/_resolve.html", context)


class LabelOutputView(LoginAndPermissionRequiredMixin, View):
    """
    Renders the actual printable document.

    The spec is re-parsed here rather than trusted from the client, so the output always
    matches what the server would show in the preview.
    """

    permission_required = "assets.view_asset"

    def get(self, request):
        context = _resolve(request.GET)
        spec, template = context["spec"], context["template"]
        if not spec.is_printable:
            return HttpResponseBadRequest("; ".join(spec.errors) or "Nothing to print")

        content = template.render(spec.assets(), offset=context["offset"])
        filename = f"labels-{timezone.localdate():%Y-%m-%d}.{template.extension}"
        disposition = "attachment" if request.GET.get("download") else "inline"
        response = HttpResponse(content, content_type=template.content_type)
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        return response
