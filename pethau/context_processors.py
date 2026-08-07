from django.conf import settings


def site(request):
    return {"SITE_LOGO": settings.SITE_LOGO}
