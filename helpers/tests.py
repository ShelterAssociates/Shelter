from django.test import SimpleTestCase

from django.test.utils import override_settings

from helpers.services.google_drive import (
    BinaryAESCipher,
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

    def test_get_upload_context_uses_event_name_for_events(self):
        upload_context = get_upload_context("events", "Health Camp 2026")
        self.assertEqual(upload_context["category_key"], "events")
        self.assertEqual(upload_context["category_folder"], "Health Camp 2026")

    def test_get_upload_context_uses_label_for_regular_categories(self):
        upload_context = get_upload_context("mhm")
        self.assertEqual(upload_context["category_label"], "MHM")
        self.assertEqual(upload_context["category_folder"], "MHM")

    def test_build_upload_file_name_uses_today_and_sequence(self):
        generated_name = build_upload_file_name(2, "photo.PNG")
        self.assertRegex(generated_name, r"^\d{4}-\d{2}-\d{2}_2\.png$")
