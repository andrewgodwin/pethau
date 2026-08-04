"""
URL configuration for pethau project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

from assets.views.asset import (
    AssetCreateView,
    AssetDeleteView,
    AssetDetailView,
    AssetListView,
    AssetUpdateView,
)
from assets.views.model import (
    ModelCreateView,
    ModelDeleteView,
    ModelDetailView,
    ModelListView,
    ModelUpdateView,
)

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="asset-list", permanent=False)),
    path("assets/", AssetListView.as_view(), name="asset-list"),
    path("assets/new/", AssetCreateView.as_view(), name="asset-create"),
    path("assets/<int:pk>/", AssetDetailView.as_view(), name="asset-detail"),
    path("assets/<int:pk>/edit/", AssetUpdateView.as_view(), name="asset-edit"),
    path("assets/<int:pk>/delete/", AssetDeleteView.as_view(), name="asset-delete"),
    path("models/", ModelListView.as_view(), name="model-list"),
    path("models/new/", ModelCreateView.as_view(), name="model-create"),
    path("models/<int:pk>/", ModelDetailView.as_view(), name="model-detail"),
    path("models/<int:pk>/edit/", ModelUpdateView.as_view(), name="model-edit"),
    path("models/<int:pk>/delete/", ModelDeleteView.as_view(), name="model-delete"),
    path("admin/", admin.site.urls),
]
