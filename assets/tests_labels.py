import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from assets.labels import TEMPLATES, get_template, parse_spec
from assets.models import Asset, Model, Owner

User = get_user_model()

# Counts page objects in a PDF ("/Type /Pages" is the page tree, not a page)
PAGE_RE = re.compile(rb"/Type\s*/Page[^s]")


@override_settings(
    ASSET_TAG_PREFIX="AER", ASSET_TAG_DIGITS=5, SITE_URL="https://example.com"
)
class LabelSpecParsingTests(TestCase):
    """
    Tests for the compact spec language, e.g. "345x2,123-125".
    """

    @classmethod
    def setUpTestData(cls):
        cls.owner = Owner.objects.create(name="Household")
        cls.model = Model.objects.create(name="Widget", manufacturer="Acme")
        # AER00004 is deliberately absent, so ranges have a gap to step over
        cls.assets = {
            number: Asset.objects.create(
                tag=f"AER{number:05d}",
                name=f"Thing {number}",
                owner=cls.owner,
                model=cls.model,
            )
            for number in (1, 2, 3, 5)
        }
        cls.deleted = Asset.objects.create(
            tag="AER00009", owner=cls.owner, model=cls.model, deleted=timezone.now()
        )

    def test_empty_spec_is_not_printable(self):
        """
        An empty spec produces no items and no errors, but nothing to print.
        """
        spec = parse_spec("")
        self.assertEqual(spec.items, [])
        self.assertEqual(spec.errors, [])
        self.assertFalse(spec.is_printable)

    def test_quantity_suffixes_are_equivalent(self):
        """
        "1x2", "1X2" and "1#2" all mean two copies.
        """
        for text in ("1x2", "1X2", "1#2"):
            spec = parse_spec(text)
            self.assertEqual(spec.errors, [], text)
            self.assertEqual(len(spec.items), 1, text)
            self.assertEqual(spec.items[0].asset, self.assets[1], text)
            self.assertEqual(spec.total, 2, text)

    def test_range_expands_inclusively(self):
        """
        A range covers both of its endpoints.
        """
        spec = parse_spec("1-3")
        self.assertEqual(
            [item.asset.tag for item in spec.items],
            ["AER00001", "AER00002", "AER00003"],
        )
        self.assertEqual(spec.total, 3)

    def test_range_with_quantity_applies_to_each_member(self):
        """
        "1-3x2" is two copies of each of the three tags.
        """
        spec = parse_spec("1-3x2")
        self.assertEqual(len(spec.items), 3)
        self.assertEqual(spec.total, 6)

    def test_mixed_separators_and_tag_forms(self):
        """
        Commas, spaces and newlines all separate terms, and tags may be written bare,
        zero-padded, or with their prefix in any case.
        """
        spec = parse_spec("AER00001, 00002\naer00003 5")
        self.assertEqual(spec.errors, [])
        self.assertEqual(
            [item.asset.tag for item in spec.items],
            ["AER00001", "AER00002", "AER00003", "AER00005"],
        )

    def test_repeated_references_accumulate(self):
        """
        Mentioning the same asset twice adds the quantities together.
        """
        spec = parse_spec("1,1x2")
        self.assertEqual(len(spec.items), 1)
        self.assertEqual(spec.total, 3)

    def test_the_users_example(self):
        """
        "345x2,123-125" style input: two of one tag and one each of a range.
        """
        spec = parse_spec("1x2,2-3")
        self.assertEqual(spec.errors, [])
        self.assertEqual(
            [(item.asset.tag, item.quantity) for item in spec.items],
            [("AER00001", 2), ("AER00002", 1), ("AER00003", 1)],
        )
        self.assertEqual(spec.total, 4)

    def test_unknown_tag_is_an_error(self):
        """
        A single reference to a tag that doesn't exist blocks printing.
        """
        spec = parse_spec("404")
        self.assertEqual(spec.items, [])
        self.assertEqual(len(spec.errors), 1)
        self.assertFalse(spec.is_printable)

    def test_deleted_asset_is_an_error(self):
        """
        Soft-deleted assets are treated as not existing.
        """
        spec = parse_spec("AER00009")
        self.assertFalse(spec.is_printable)
        self.assertEqual(len(spec.errors), 1)

    def test_range_gap_is_a_notice_not_an_error(self):
        """
        Missing members of a range are skipped and reported, but still printable.
        """
        spec = parse_spec("1-5")
        self.assertEqual(spec.errors, [])
        self.assertEqual(len(spec.notices), 1)
        self.assertIn("AER00004", spec.notices[0])
        self.assertEqual(
            [item.asset.tag for item in spec.items],
            ["AER00001", "AER00002", "AER00003", "AER00005"],
        )

    def test_range_with_no_members_is_an_error(self):
        """
        A range that matches nothing at all is a typo, not an empty selection.
        """
        spec = parse_spec("100-110")
        self.assertFalse(spec.is_printable)
        self.assertTrue(spec.errors)

    def test_out_of_bounds_quantities_are_errors(self):
        """
        Quantities must be between 1 and 99.
        """
        for text in ("1x0", "1x100"):
            spec = parse_spec(text)
            self.assertTrue(spec.errors, text)

    def test_backwards_and_oversized_ranges_are_errors(self):
        """
        Ranges must run forwards and stay within the size cap.
        """
        for text in ("3-1", "1-2000"):
            spec = parse_spec(text)
            self.assertTrue(spec.errors, text)

    def test_unparseable_terms_are_errors(self):
        """
        Anything that isn't a tag or a range is reported rather than ignored.
        """
        spec = parse_spec("hello, 1")
        self.assertTrue(spec.errors)
        self.assertFalse(spec.is_printable)

    def test_assets_flattens_by_quantity(self):
        """
        `assets()` yields one entry per physical label, in order.
        """
        spec = parse_spec("1x2,2")
        self.assertEqual(
            [asset.tag for asset in spec.assets()], ["AER00001", "AER00001", "AER00002"]
        )


@override_settings(
    ASSET_TAG_PREFIX="AER", ASSET_TAG_DIGITS=5, SITE_URL="https://example.com"
)
class LabelRenderingTests(TestCase):
    """
    Tests for the shipped label templates.
    """

    @classmethod
    def setUpTestData(cls):
        cls.owner = Owner.objects.create(name="Household")
        cls.model = Model.objects.create(name="Widget", manufacturer="Acme")
        cls.assets = [
            Asset.objects.create(
                tag=f"AER{number:05d}",
                name=f"Thing {number}",
                owner=cls.owner,
                model=cls.model,
            )
            for number in range(1, 32)
        ]

    def test_every_template_renders(self):
        """
        All registered templates produce non-empty output for a single asset.
        """
        for slug, template in TEMPLATES.items():
            self.assertTrue(template.render(self.assets[:1]), slug)

    def test_pdf_templates_produce_a_pdf(self):
        """
        The sheet templates emit a real PDF.
        """
        for slug in ("avery-5160", "avery-6467"):
            content = get_template(slug).render(self.assets[:3])
            self.assertTrue(content.startswith(b"%PDF"), slug)

    def test_sheet_paginates_when_full(self):
        """
        31 labels don't fit on a 30-up Avery 5160 sheet, so they spill onto a second
        page.
        """
        template = get_template("avery-5160")
        self.assertEqual(len(PAGE_RE.findall(template.render(self.assets[:30]))), 1)
        self.assertEqual(len(PAGE_RE.findall(template.render(self.assets[:31]))), 2)

    def test_offset_skips_labels(self):
        """
        An offset leaves that many cells blank, pushing later labels onto the next page.
        """
        template = get_template("avery-5160")
        self.assertEqual(
            len(PAGE_RE.findall(template.render(self.assets[:2], offset=29))), 2
        )

    def test_zpl_wraps_each_label(self):
        """
        ZPL output is one ^XA/^XZ block per physical label, containing the tag.
        """
        template = get_template("zebra-3x1")
        content = template.render(
            [self.assets[0], self.assets[0], self.assets[1]]
        ).decode()
        self.assertTrue(content.startswith("^XA"))
        self.assertTrue(content.strip().endswith("^XZ"))
        self.assertEqual(content.count("^XA"), 3)
        self.assertEqual(content.count("AER00001"), 4)  # barcode + text, twice


@override_settings(
    ASSET_TAG_PREFIX="AER", ASSET_TAG_DIGITS=5, SITE_URL="https://example.com"
)
class LabelViewTests(TestCase):
    """
    Tests for the label printing page and its output endpoint.
    """

    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", name="User")
        self.user.user_permissions.add(
            *Permission.objects.filter(codename="view_asset")
        )
        self.client.force_login(self.user)
        self.owner = Owner.objects.create(name="Household")
        self.model = Model.objects.create(name="Widget", manufacturer="Acme")
        self.asset = Asset.objects.create(
            tag="AER00001", name="Thing", owner=self.owner, model=self.model
        )

    def test_print_page_prefills_from_query(self):
        """
        The page pre-fills its spec from ?spec=, as linked from an asset's detail page.
        """
        response = self.client.get(reverse("label-print"), {"spec": "AER00001"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AER00001")

    def test_resolve_lists_assets_and_remembers_template(self):
        """
        The HTMX preview resolves the spec and stores the chosen template in the
        session.
        """
        response = self.client.get(
            reverse("label-resolve"),
            {"spec": "1x2", "template": "avery-6467", "offset": "3"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AER00001")
        self.assertContains(response, "&times;2")
        self.assertEqual(
            self.client.session["label_print"], {"template": "avery-6467", "offset": 3}
        )

    def test_resolve_shows_zpl_for_zpl_templates(self):
        """
        Selecting a ZPL template shows the generated ZPL on the page.
        """
        response = self.client.get(
            reverse("label-resolve"), {"spec": "1", "template": "zebra-3x1"}
        )
        self.assertContains(response, "^XA")
        self.assertContains(response, "Download .zpl")

    def test_pdf_output_is_inline(self):
        """
        PDF output is served inline so the browser's viewer opens it.
        """
        response = self.client.get(
            reverse("label-output"), {"spec": "1", "template": "avery-5160"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response["Content-Disposition"].startswith("inline;"))
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_zpl_output_can_be_downloaded(self):
        """
        The ZPL button asks for a download, which comes back as an attachment.
        """
        response = self.client.get(
            reverse("label-output"),
            {"spec": "1", "template": "zebra-3x1", "download": "1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))
        self.assertIn(".zpl", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"^XA"))

    def test_output_rejects_an_unprintable_spec(self):
        """
        A spec with errors is refused rather than silently printing a subset.
        """
        response = self.client.get(
            reverse("label-output"), {"spec": "404", "template": "avery-5160"}
        )
        self.assertEqual(response.status_code, 400)

    def test_output_rejects_an_empty_spec(self):
        """
        An empty spec has nothing to print.
        """
        response = self.client.get(
            reverse("label-output"), {"spec": "", "template": "avery-5160"}
        )
        self.assertEqual(response.status_code, 400)
