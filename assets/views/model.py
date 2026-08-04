from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from assets.forms import ModelForm
from assets.models import Model


class ModelListView(ListView):
    model = Model
    template_name = "model_list.html"
    context_object_name = "models"
    queryset = Model.objects.order_by("manufacturer", "name")


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
