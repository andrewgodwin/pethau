from ninja.errors import HttpError


def require_permission(request, perm):
    """
    Call as the first line of a route function.

    By the time route code runs, django-ninja has already returned 401 if no auth class
    succeeded, so request.user is guaranteed to be an authenticated user here.
    """
    if not request.user.has_perm(perm):
        raise HttpError(403, "You do not have permission to perform this action.")
