from django.test import SimpleTestCase

from django.test.utils import override_settings

from helpers.services.google_drive import (
    BinaryAESCipher,
    build_drive_path,
    build_upload_file_name,
    clean_drive_name,
    get_slum_hierarchy,
    get_upload_context,
)


@override_settings(CIPHER_KEY='Sh5lt5rS@ftc@rn3')
class PhotoUploadHelpersTests(SimpleTestCase):
    def test_clean_drive_name_replaces_invalid_characters(self):
        self.assertEqual(clean_drive_name(' Pune/City:*?"<>| '), "Pune_City_")

    def test_get_slum_hierarchy_uses_all_master_levels(self):
        city_reference = type("CityReference", (), {"city_name": "Mumbai"})()
        city = type("City", (), {"name": city_reference})()
        admin_ward = type("AdministrativeWard", (), {"name": "Ward A", "city": city})()
        electoral_ward = type("ElectoralWard", (), {"name": "Electoral 5", "administrative_ward": admin_ward})()
        slum = type("Slum", (), {"name": "Janta Nagar", "electoral_ward": electoral_ward})()

        hierarchy = get_slum_hierarchy(slum)
        self.assertEqual(hierarchy["city"], "Mumbai")
        self.assertEqual(hierarchy["administrative_ward"], "Ward A")
        self.assertEqual(hierarchy["electoral_ward"], "Electoral 5")
        self.assertEqual(hierarchy["slum"], "Janta Nagar")

    def test_binary_cipher_encrypts_and_decrypts_bytes(self):
        raw = b"compressed-zip-binary"
        cipher = BinaryAESCipher()
        encrypted = cipher.encrypt_bytes(raw)
        self.assertNotEqual(encrypted, raw)
        self.assertEqual(cipher.decrypt_bytes(encrypted), raw)

    def test_get_upload_context_uses_path_nodes(self):
        root = type("Node", (), {"name": "Activity"})()
        leaf = type("Node", (), {"name": "Festival"})()

        class PhotoType:
            name = "Festival"

            def path_nodes(self):
                return [root, leaf]

        upload_context = get_upload_context(PhotoType())
        self.assertEqual(upload_context["category_label"], "Festival")
        self.assertEqual(upload_context["category_path"], ["Activity", "Festival"])

    def test_build_upload_file_name_uses_uuid_and_preserves_extension(self):
        generated_name = build_upload_file_name("photo.PNG")
        self.assertRegex(generated_name, r"^[0-9a-f-]{36}\.png$")

    def test_build_drive_path_supports_normal_city_level_and_custom_uploads(self):
        city_reference = type("CityReference", (), {"city_name": "Pune"})()
        city = type("City", (), {"name": city_reference})()
        admin_ward = type("AdministrativeWard", (), {"name": "A12", "city": city})()
        electoral_ward = type("ElectoralWard", (), {"name": "E5", "administrative_ward": admin_ward})()
        slum = type("Slum", (), {"name": "GaneshNagar", "electoral_ward": electoral_ward})()

        class PhotoType:
            name = "Festival"

            def path_nodes(self):
                return [type("Node", (), {"name": "Activity"})(), type("Node", (), {"name": "Festival"})()]

        photo_type = PhotoType()

        normal = build_drive_path("2026-05-28", project_type="PHOT", photo_type_item=photo_type, slum=slum)
        self.assertEqual(normal["drive_path_parts"], ["PHOT", "Pune", "GaneshNagar_A12_E5", "Activity", "Festival", "2026-05-28"])
        self.assertEqual(normal["project_type"], "PHOT")

        city_level = build_drive_path("2026-05-28", project_type="MHM", photo_type_item=photo_type, city=city, is_city_level=True)
        self.assertEqual(city_level["drive_path_parts"], ["MHM", "Pune", "Activity", "Festival", "2026-05-28"])

        custom = build_drive_path("2026-05-28", project_type="Other", project_type_other="Community", is_other_upload=True, custom_folder_name="FloodReliefPhotos")
        self.assertEqual(custom["drive_path_parts"], ["Other", "Community", "FloodReliefPhotos", "2026-05-28"])
