from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from assets.forms import ModelForm
from assets.models import Model


class ModelListView(ListView):
    model = Model
    template_name = "model/list.html"
    context_object_name = "models"
    paginate_by = 100

    def get_queryset(self):
        queryset = Model.objects.select_related("image").order_by(
            "manufacturer", "name"
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(manufacturer__icontains=query)
                | Q(short_name__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        return context


class ModelDetailView(DetailView):
    model = Model
    template_name = "model/detail.html"
    context_object_name = "model"


class ModelCreateView(CreateView):
    model = Model
    form_class = ModelForm
    template_name = "model/form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        form.save_image(self.object)
        return response


class ModelUpdateView(UpdateView):
    model = Model
    form_class = ModelForm
    template_name = "model/form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        form.save_image(self.object)
        return response


class ModelDeleteView(DeleteView):
    model = Model
    template_name = "model/confirm_delete.html"
    success_url = reverse_lazy("model-list")


class ModelSearchView(ListView):
    """
    HTMX partial: returns a filtered, capped list of models for the search-as-you-type
    combo box on the asset form.
    """

    model = Model
    template_name = "model/_search_options.html"
    context_object_name = "models"

    def get_queryset(self):
        queryset = Model.objects.order_by("manufacturer", "name")
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(manufacturer__icontains=query)
                | Q(short_name__icontains=query)
            )
        return queryset[:20]


class ModelQuickCreateView(CreateView):
    """
    HTMX partial: renders/handles the "+" popup form for creating a model without
    leaving the asset form.
    """

    model = Model
    form_class = ModelForm
    template_name = "model/_quick_create.html"

    def form_valid(self, form):
        self.object = form.save()
        return self.render_to_response(
            self.get_context_data(form=None, model=self.object)
        )
