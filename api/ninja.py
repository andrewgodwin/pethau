from django.contrib.auth.decorators import login_required
from ninja import NinjaAPI
from ninja.security import django_auth

from api.auth import ApiKeyAuth
from assets.api.routers import router as assets_router

api = NinjaAPI(
    title="Pethau API",
    # Every route is GET-only (read-only API), so session-authenticated requests are
    # never subject to Django's CSRF checks regardless -- revisit this if a write
    # endpoint is ever added.
    auth=[django_auth, ApiKeyAuth()],
    docs_decorator=login_required,
)

api.add_router("/assets/", assets_router)
