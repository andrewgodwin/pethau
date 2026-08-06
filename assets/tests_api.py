from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone

from accounts.models import ApiKey
from assets.models import Asset, AssetHistory, AssetIdentifier, Model, Owner

User = get_user_model()


class ApiTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", name="User")
        self.owner = Owner.objects.create(name="Household", notes="Owner notes")
        self.model = Model.objects.create(name="Widget", manufacturer="Acme")
        self.asset = Asset.objects.create(
            tag="AER00001", owner=self.owner, model=self.model, notes="Asset notes"
        )
        self.history = AssetHistory.objects.create(
            asset=self.asset, status="active", notes="History notes"
        )
        self.asset.current_history = self.history
        self.asset.save(update_fields=["current_history"])
        AssetIdentifier.objects.create(
            asset=self.asset, kind="rfid_uhf", value="TAG-VALUE"
        )

    def grant(self, *codenames):
        self.user.user_permissions.add(
            *Permission.objects.filter(codename__in=codenames)
        )

    def make_key(self, user=None):
        raw_token, prefix, hashed_key = ApiKey.generate()
        api_key = ApiKey.objects.create(
            user=user or self.user, prefix=prefix, hashed_key=hashed_key
        )
        return raw_token, api_key

    def auth_headers(self, raw_token):
        return {"HTTP_AUTHORIZATION": f"Bearer {raw_token}"}


class ApiKeyModelTests(TestCase):
    def test_generate_and_hash_round_trip(self):
        raw_token, prefix, hashed_key = ApiKey.generate()
        self.assertEqual(prefix, raw_token[:8])
        self.assertEqual(hashed_key, ApiKey.hash_token(raw_token))


class SessionAuthTests(ApiTestCase):
    def test_anonymous_gets_401(self):
        response = self.client.get("/api/v1/assets/")
        self.assertEqual(response.status_code, 401)

    def test_logged_in_without_permission_forbidden(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/v1/assets/")
        self.assertEqual(response.status_code, 403)

    def test_logged_in_with_permission_allowed(self):
        self.grant("view_asset")
        self.client.force_login(self.user)
        response = self.client.get("/api/v1/assets/")
        self.assertEqual(response.status_code, 200)


class ApiKeyAuthTests(ApiTestCase):
    def test_missing_header_gets_401(self):
        response = self.client.get("/api/v1/assets/")
        self.assertEqual(response.status_code, 401)

    def test_garbage_token_gets_401(self):
        response = self.client.get(
            "/api/v1/assets/", **self.auth_headers("not-a-real-token")
        )
        self.assertEqual(response.status_code, 401)

    def test_key_for_inactive_user_gets_401(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        raw_token, _ = self.make_key()
        response = self.client.get("/api/v1/assets/", **self.auth_headers(raw_token))
        self.assertEqual(response.status_code, 401)

    def test_valid_key_without_permission_forbidden(self):
        raw_token, _ = self.make_key()
        response = self.client.get("/api/v1/assets/", **self.auth_headers(raw_token))
        self.assertEqual(response.status_code, 403)

    def test_valid_key_with_permission_allowed(self):
        self.grant("view_asset")
        raw_token, _ = self.make_key()
        response = self.client.get("/api/v1/assets/", **self.auth_headers(raw_token))
        self.assertEqual(response.status_code, 200)

    def test_valid_key_updates_last_used(self):
        self.grant("view_asset")
        raw_token, api_key = self.make_key()
        self.assertIsNone(api_key.last_used)
        self.client.get("/api/v1/assets/", **self.auth_headers(raw_token))
        api_key.refresh_from_db()
        self.assertIsNotNone(api_key.last_used)
        first_used = api_key.last_used

        self.client.get("/api/v1/assets/", **self.auth_headers(raw_token))
        api_key.refresh_from_db()
        self.assertGreaterEqual(api_key.last_used, first_used)

    def test_deleted_key_gets_401(self):
        self.grant("view_asset")
        raw_token, api_key = self.make_key()
        api_key.delete()
        response = self.client.get("/api/v1/assets/", **self.auth_headers(raw_token))
        self.assertEqual(response.status_code, 401)


class AssetDetailEndpointTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.grant("view_asset")
        self.client.force_login(self.user)

    def test_detail_by_pk(self):
        response = self.client.get(f"/api/v1/assets/{self.asset.pk}/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["tag"], "AER00001")
        self.assertEqual(body["notes"], "Asset notes")
        self.assertEqual(body["model"]["name"], "Widget")
        self.assertEqual(body["model"]["display_name"], "Acme Widget")
        self.assertEqual(body["owner"]["notes"], "Owner notes")
        self.assertEqual(body["current_history"]["notes"], "History notes")
        self.assertEqual(body["current_history"]["status_display"], "Active")
        self.assertEqual(len(body["identifiers"]), 1)
        self.assertEqual(body["identifiers"][0]["value"], "TAG-VALUE")

    def test_detail_soft_deleted_returns_404(self):
        self.asset.deleted = timezone.now()
        self.asset.save(update_fields=["deleted"])
        response = self.client.get(f"/api/v1/assets/{self.asset.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_detail_nonexistent_pk_returns_404(self):
        response = self.client.get("/api/v1/assets/999999/")
        self.assertEqual(response.status_code, 404)

    def test_detail_by_exact_tag(self):
        response = self.client.get("/api/v1/assets/by-tag/AER00001/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tag"], "AER00001")

    def test_detail_by_numeric_suffix(self):
        response = self.client.get("/api/v1/assets/by-tag/1/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tag"], "AER00001")

    def test_detail_by_ambiguous_numeric_suffix_returns_404(self):
        Asset.objects.create(tag="OTH00001", owner=self.owner, model=self.model)
        response = self.client.get("/api/v1/assets/by-tag/1/")
        self.assertEqual(response.status_code, 404)

    def test_detail_by_tag_of_soft_deleted_asset_returns_404(self):
        self.asset.deleted = timezone.now()
        self.asset.save(update_fields=["deleted"])
        response = self.client.get("/api/v1/assets/by-tag/AER00001/")
        self.assertEqual(response.status_code, 404)


class AssetListEndpointTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.grant("view_asset")
        self.client.force_login(self.user)

    def test_response_shape(self):
        response = self.client.get("/api/v1/assets/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("items", body)
        self.assertIn("count", body)
        self.assertEqual(body["count"], 1)

    def test_excludes_soft_deleted(self):
        self.asset.deleted = timezone.now()
        self.asset.save(update_fields=["deleted"])
        response = self.client.get("/api/v1/assets/")
        self.assertEqual(response.json()["count"], 0)

    def test_query_filters_by_tag_or_name(self):
        Asset.objects.create(
            tag="OTH00001", name="Other", owner=self.owner, model=self.model
        )
        response = self.client.get("/api/v1/assets/", {"q": "AER"})
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["items"][0]["tag"], "AER00001")

    def test_list_item_includes_embedded_model(self):
        response = self.client.get("/api/v1/assets/")
        item = response.json()["items"][0]
        self.assertEqual(item["model"]["display_name"], "Acme Widget")


class AssetSearchEndpointTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.grant("view_asset")
        self.client.force_login(self.user)

    def test_digit_query_matches_tag_suffix(self):
        response = self.client.get("/api/v1/assets/search/", {"q": "1"})
        tags = [item["tag"] for item in response.json()]
        self.assertIn("AER00001", tags)

    def test_nondigit_query_matches_tag_substring(self):
        response = self.client.get("/api/v1/assets/search/", {"q": "AER0000"})
        tags = [item["tag"] for item in response.json()]
        self.assertIn("AER00001", tags)

    def test_exclude_param_removes_asset(self):
        response = self.client.get("/api/v1/assets/search/", {"exclude": self.asset.pk})
        tags = [item["tag"] for item in response.json()]
        self.assertNotIn("AER00001", tags)

    def test_results_capped_at_twenty(self):
        for i in range(25):
            Asset.objects.create(tag=f"CAP{i:05d}", owner=self.owner, model=self.model)
        response = self.client.get("/api/v1/assets/search/")
        self.assertEqual(len(response.json()), 20)


class ApiDocsAccessTests(TestCase):
    def test_anonymous_docs_redirected_to_login(self):
        response = self.client.get("/api/v1/docs")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_anonymous_openapi_json_redirected_to_login(self):
        response = self.client.get("/api/v1/openapi.json")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_logged_in_docs_allowed(self):
        user = User.objects.create_user(email="staff@example.com", name="Staff")
        self.client.force_login(user)
        response = self.client.get("/api/v1/docs")
        self.assertEqual(response.status_code, 200)
