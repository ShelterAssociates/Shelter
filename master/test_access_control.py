"""Pages hidden from a user's menu must also be refused by the server."""

from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse

from avni.tests.support import make_city

LOGIN = "/accounts/login/"


def perm(codename):
    return Permission.objects.get(codename=codename)


class AccessControlCase(TestCase):
    def setUp(self):
        self.plain = User.objects.create_user("sunita", password="x")
        self.staff = User.objects.create_user("staffer", password="x", is_staff=True)
        self.admin = User.objects.create_superuser("shelter", "s@example.org", "x")

    def assert_sent_to_login(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(LOGIN), response["Location"])


class SurveyMappingTests(AccessControlCase):
    def test_anonymous_user_is_sent_to_login(self):
        self.assert_sent_to_login(self.client.get("/admin/surveymapping/"))

    def test_user_without_view_survey_gets_403(self):
        self.client.force_login(self.plain)
        self.assertEqual(self.client.get("/admin/surveymapping/").status_code, 403)

    def test_staff_without_view_survey_gets_403(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/admin/surveymapping/").status_code, 403)

    def test_user_with_view_survey_sees_the_list_and_the_filter_works(self):
        self.plain.user_permissions.add(perm("view_survey"))
        self.client.force_login(self.plain)
        self.assertEqual(self.client.get("/admin/surveymapping/").status_code, 200)
        self.assertEqual(self.client.get("/admin/surveymapping/Pune/").status_code, 200)
        self.assertEqual(self.client.get("/admin/surveymapping/P/").status_code, 200)
        self.assertEqual(self.client.get("/admin/surveymapping/Navi mumbai/").status_code, 200)

    def test_filter_route_is_protected_too(self):
        self.client.force_login(self.plain)
        self.assertEqual(self.client.get("/admin/surveymapping/Pune/").status_code, 403)


class StaffOnlyReportTests(AccessControlCase):
    PAGES = ("/admin/report/", "/admin/vulnerabilityReport/", "/helpers/digipin_generate/")
    AJAX = ("/admin/rimreportgenerate/", "/admin/drainagereportgenerate/")

    def test_anonymous_and_non_staff_users_are_sent_to_login(self):
        for url in self.PAGES + self.AJAX:
            self.assert_sent_to_login(self.client.get(url))
        self.client.force_login(self.plain)
        for url in self.PAGES + self.AJAX:
            self.assert_sent_to_login(self.client.get(url))

    def test_staff_can_open_them(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/admin/report/").status_code, 200)
        self.assertEqual(self.client.get("/helpers/digipin_generate/").status_code, 200)
        response = self.client.get("/admin/vulnerabilityReport/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("Vulnerability_Report", response["Location"])


class LocationLookupTests(AccessControlCase):
    def test_ward_and_slum_lookups_need_a_login(self):
        city = make_city()
        for url in ("/admin/cityList/", "/admin/administrativewardList/", "/admin/electoralWardList/", "/admin/slumList/"):
            self.assert_sent_to_login(self.client.post(url, {"id": city.id}))
        self.client.force_login(self.plain)
        self.assertEqual(self.client.post("/admin/administrativewardList/", {"id": city.id}).status_code, 200)


@override_settings(GRAPH_DETAILS={"toilet_construction": ("fixture", 7)}, GRAPHS_BUILD_URL="/graph/%s/%s")
class GraphPermissionTests(AccessControlCase):
    def test_logged_in_user_without_mastersheet_permission_gets_403(self):
        self.client.force_login(self.plain)
        self.assertEqual(self.client.get("/graphs/type/toilet_construction/").status_code, 403)
        self.assertEqual(self.client.get("/graphs/covid_data/").status_code, 403)

    def test_either_mastersheet_permission_opens_the_graphs(self):
        for codename in ("can_view_mastersheet", "can_view_mastersheet_report"):
            user = User.objects.create_user("viewer_" + codename, password="x")
            user.user_permissions.add(perm(codename))
            self.client.force_login(user)
            self.assertEqual(self.client.get("/graphs/type/toilet_construction/").status_code, 200, codename)
            self.assertEqual(self.client.get("/graphs/covid_data/").status_code, 200, codename)

    def test_unknown_graph_type_is_404_not_500(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/graphs/type/no_such_graph/").status_code, 404)


class LoginRedirectTests(AccessControlCase):
    def test_next_pointing_to_another_site_is_ignored(self):
        self.client.force_login(self.staff)
        for target in ("https://attacker.com/", "//attacker.com/", "https:attacker.com"):
            response = self.client.get(reverse("login_success"), {"next": target})
            self.assertEqual(response["Location"], "/admin/", target)

    def test_next_on_this_site_is_followed(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("login_success"), {"next": "/mastersheet/show/mastersheet/"})
        self.assertEqual(response["Location"], "/mastersheet/show/mastersheet/")


class AdminKMLUploadPermissionTests(AccessControlCase):
    def test_staff_without_change_permission_cannot_upload_boundaries(self):
        city = make_city()
        self.staff.user_permissions.add(perm("view_city"))
        self.client.force_login(self.staff)
        for name in ("city-kml-upload", "adminward-kml-upload", "electoralward-kml-upload", "slum-kml-upload"):
            response = self.client.post(reverse("admin:" + name, args=[city.pk]))
            self.assertEqual(response.status_code, 403, name)
            self.assertFalse(response.json()["status"])

    def test_superuser_passes_the_permission_check(self):
        city = make_city()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin:city-kml-upload", args=[city.pk])).status_code, 200)


class ApiWritePermissionTests(AccessControlCase):
    """The API authenticates with Basic auth or a token, so any account (e.g. a sponsor) can call it."""

    def api(self, user=None):
        from rest_framework.test import APIClient
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client

    def test_logged_in_user_can_read_but_not_change_cities_or_metadata(self):
        from django.contrib.auth.models import Group
        city = make_city()
        self.plain.groups.add(Group.objects.create(name="city:Thane"))
        client = self.api(self.plain)
        self.assertEqual(client.get("/api/city/").status_code, 200)
        self.assertEqual(client.delete("/api/city/%d/" % city.pk).status_code, 403)
        self.assertEqual(client.post("/api/city/", {}).status_code, 403)
        self.assertEqual(client.post("/api/metadata/?slum_id=1", {}).status_code, 403)
        self.assertTrue(type(city).objects.filter(pk=city.pk).exists())

    def test_anonymous_user_cannot_read(self):
        self.assertIn(self.api().get("/api/city/").status_code, (401, 403))

    def test_user_with_model_permission_may_write(self):
        make_city()
        self.assertNotEqual(self.api(self.admin).post("/api/city/", {}).status_code, 403)


class MastersheetDetailsTests(AccessControlCase):
    def test_slum_details_endpoint_needs_a_mastersheet_permission(self):
        self.assert_sent_to_login(self.client.get("/mastersheet/details/"))
        self.client.force_login(self.plain)
        self.assertEqual(self.client.get("/mastersheet/details/").status_code, 403)
        self.plain.user_permissions.add(perm("can_view_mastersheet"))
        self.assertNotEqual(self.client.get("/mastersheet/details/").status_code, 403)



class SlumInformationPagesTests(AccessControlCase):
    DISPLAY, INSERT = "/admin/sluminformation/drainage/display/", "/admin/sluminformation/drainage/insert/"

    def test_anonymous_user_is_sent_to_login(self):
        for url in ("/admin/sluminformation/", self.DISPLAY, self.INSERT):
            self.assert_sent_to_login(self.client.get(url))

    def test_user_without_view_drainage_gets_403(self):
        self.client.force_login(self.plain)
        for url in (self.DISPLAY, self.INSERT):
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_view_permission_opens_the_list_but_not_the_form(self):
        self.plain.user_permissions.add(perm("view_drainage"))
        self.client.force_login(self.plain)
        self.assertEqual(self.client.get("/admin/sluminformation/").status_code, 200)
        self.assertEqual(self.client.get(self.DISPLAY).status_code, 200)
        self.assertEqual(self.client.get(self.INSERT).status_code, 403)

    def test_add_permission_opens_the_form(self):
        self.plain.user_permissions.add(perm("add_drainage"))
        self.client.force_login(self.plain)
        self.assertEqual(self.client.get(self.INSERT).status_code, 200)
