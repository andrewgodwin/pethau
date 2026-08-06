from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from assets.models import Asset, Model, Owner

User = get_user_model()


class ViewAccessControlTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", name="User")
        self.owner = Owner.objects.create(name="Household")
        self.model = Model.objects.create(name="Widget")
        self.asset = Asset.objects.create(
            tag="AER00001", owner=self.owner, model=self.model
        )

    def grant(self, *codenames):
        self.user.user_permissions.add(
            *Permission.objects.filter(codename__in=codenames)
        )

    def test_anonymous_redirected_to_login(self):
        """
        Anonymous users are redirected to the login page.
        """
        response = self.client.get(reverse("asset-list"))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('asset-list')}"
        )

    def test_logged_in_without_permission_forbidden(self):
        """
        Logged-in users lacking the required permission get a 403.
        """
        self.client.force_login(self.user)
        response = self.client.get(reverse("asset-list"))
        self.assertEqual(response.status_code, 403)

    def test_logged_in_with_permission_allowed(self):
        """
        Logged-in users with the required permission can access the view.
        """
        self.grant("view_asset")
        self.client.force_login(self.user)
        response = self.client.get(reverse("asset-list"))
        self.assertEqual(response.status_code, 200)

    def test_create_requires_add_permission(self):
        """
        Creating an asset succeeds once the user holds the add permission.
        """
        self.grant("add_asset")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("asset-create"),
            {"tag": "AER00002", "owner": self.owner.pk, "model": self.model.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Asset.objects.filter(tag="AER00002").exists())

    def test_delete_requires_delete_permission(self):
        """
        Deleting an asset is forbidden without the delete permission.
        """
        self.grant("view_asset")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("asset-delete", kwargs={"pk": self.asset.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_model_list_anonymous_redirected(self):
        """
        The Model views follow the same anonymous-redirect pattern as Asset views.
        """
        response = self.client.get(reverse("model-list"))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('model-list')}"
        )

    def test_bulk_audit_anonymous_redirected(self):
        """
        Bulk-audit views also require login.
        """
        response = self.client.get(reverse("bulk-audit"))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('bulk-audit')}"
        )

    def test_bulk_audit_with_permission_allowed(self):
        """
        Bulk-audit is reachable once the user can add asset history.
        """
        self.grant("add_assethistory")
        self.client.force_login(self.user)
        response = self.client.get(reverse("bulk-audit"))
        self.assertEqual(response.status_code, 200)


class BootstrapGroupsTests(TestCase):
    def test_full_access_group_has_all_permissions(self):
        """
        The 'Full access' group holds all 12 CRUD permissions for the three models.
        """
        group = Group.objects.get(name="Full access")
        self.assertEqual(group.permissions.count(), 12)

    def test_viewer_group_has_view_only_permissions(self):
        """
        The 'Viewer' group holds only the three view permissions.
        """
        group = Group.objects.get(name="Viewer")
        self.assertEqual(
            set(group.permissions.values_list("codename", flat=True)),
            {"view_asset", "view_model", "view_assethistory"},
        )
