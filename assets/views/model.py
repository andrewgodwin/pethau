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
    template_name = "model_list.html"
    context_object_name = "models"
    paginate_by = 100

    def get_queryset(self):
        queryset = Model.objects.order_by("manufacturer", "name")
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
    template_name = "model_detail.html"
    context_object_name = "model"


class ModelCreateView(CreateView):
    model = Model
    form_class = ModelForm
    template_name = "model_form.html"


class ModelUpdateView(UpdateView):
    model = Model
    form_class = ModelForm
    template_name = "model_form.html"


class ModelDeleteView(DeleteView):
    model = Model
    template_name = "model_confirm_delete.html"
    success_url = reverse_lazy("model-list")
