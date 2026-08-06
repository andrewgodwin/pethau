from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class LoginAndPermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Requires login and `permission_required`.

    Anonymous users are redirected to LOGIN_URL; authenticated users lacking the
    permission get a 403.
    """
