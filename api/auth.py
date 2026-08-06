from django.utils import timezone
from ninja.security import HttpBearer

from accounts.models import ApiKey


class ApiKeyAuth(HttpBearer):
    """
    Authenticates a Bearer token against ApiKey.hashed_key, and makes the request act as
    that key's linked user.
    """

    def authenticate(self, request, token):
        try:
            api_key = ApiKey.objects.select_related("user").get(
                hashed_key=ApiKey.hash_token(token)
            )
        except ApiKey.DoesNotExist:
            return None
        if not api_key.user.is_active:
            return None
        ApiKey.objects.filter(pk=api_key.pk).update(last_used=timezone.now())
        # API-key requests don't go through AuthenticationMiddleware, so request.user
        # would otherwise stay AnonymousUser even after a successful key auth.
        request.user = api_key.user
        return api_key.user
