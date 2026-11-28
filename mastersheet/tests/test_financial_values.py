"""Invoices and sponsor funds: no negative amounts, and invoice totals are always computed by the server."""

from django.contrib.auth.models import User
from django.test import TestCase

from avni.tests.support import make_city, make_slum
from mastersheet.models import Invoice, InvoiceItems, MaterialType, Vendor
from sponsor.models import SponsorProject

INVOICE_URL = "/accounts/mastersheet/invoice/add/"
PROJECT_URL = "/accounts/sponsor/sponsorproject/add/"


class FinanceCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("shelter", "s@example.org", "x")
        self.client.force_login(self.admin)
        city = make_city()
        self.slum = make_slum(city)
        self.vendor = Vendor.objects.create(name="Cement Co", gst_number="G1", city=city)
        self.material = MaterialType.objects.create(name="Cement", display_flag=True, display_order=1)

    def post_invoice(self, number="INV-1", total="2000", final_total="2000", roundoff="0", transport="0",
                     quantity="10", rate="100", tax="0", households='["101", "102"]', item_total="2000"):
        return self.client.post(INVOICE_URL, {
            "vendor": self.vendor.id, "invoice_number": number, "invoice_date": "2026-11-01",
            "total": total, "loading_unloading_charges": "0", "transport_charges": transport,
            "roundoff": roundoff, "final_total": final_total,
            "invoiceitems_set-TOTAL_FORMS": "1", "invoiceitems_set-INITIAL_FORMS": "0",
            "invoiceitems_set-MIN_NUM_FORMS": "1", "invoiceitems_set-MAX_NUM_FORMS": "1000",
            "invoiceitems_set-0-material_type": self.material.id, "invoiceitems_set-0-phase": "1",
            "invoiceitems_set-0-slum": self.slum.id, "invoiceitems_set-0-household_numbers": households,
            "invoiceitems_set-0-quantity": quantity, "invoiceitems_set-0-unit": "2",
            "invoiceitems_set-0-rate": rate, "invoiceitems_set-0-tax": tax, "invoiceitems_set-0-total": item_total,
        })


class InvoiceTests(FinanceCase):
    def test_tampered_negative_totals_are_replaced_by_the_server_values(self):
        """The auditor's PoE: valid quantity/rate, total changed to a negative number in transit."""
        response = self.post_invoice(total="-5000", final_total="-100000", item_total="-3000")
        self.assertEqual(response.status_code, 302, response.content[:2000])
        invoice = Invoice.objects.get(invoice_number="INV-1")
        self.assertEqual((invoice.total, invoice.final_total), (2000.0, 2000.0))
        self.assertEqual(InvoiceItems.objects.get(invoice=invoice).total, 2000.0)

    def test_tax_and_charges_are_part_of_the_server_total(self):
        self.post_invoice(tax="18", transport="50", roundoff="-0.5", total="1", final_total="1", item_total="1")
        invoice = Invoice.objects.get(invoice_number="INV-1")
        self.assertEqual((invoice.total, invoice.final_total), (2360.0, 2409.5))

    def test_negative_quantity_rate_tax_and_charges_are_refused(self):
        for field, value in (("quantity", "-10"), ("rate", "-100"), ("tax", "-18"), ("tax", "150"),
                             ("transport", "-10"), ("roundoff", "-5000"), ("rate", "1e12")):
            response = self.post_invoice(number="BAD-%s-%s" % (field, value), **{field: value})
            self.assertEqual(response.status_code, 200, (field, value))
            self.assertFalse(Invoice.objects.filter(invoice_number="BAD-%s-%s" % (field, value)).exists(), (field, value))

    def test_negative_final_total_through_roundoff_is_refused(self):
        response = self.post_invoice(quantity="0", roundoff="-1")
        self.assertContains(response, "cannot be negative")
        self.assertFalse(Invoice.objects.exists())

    def test_households_must_be_a_list(self):
        response = self.post_invoice(households='"101"')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Invoice.objects.exists())

    def test_refused_duplicate_households_still_leave_server_totals(self):
        self.post_invoice(number="FIRST")
        self.post_invoice(number="SECOND", total="-5000", final_total="-5000", item_total="-5000")
        second = Invoice.objects.get(invoice_number="SECOND")
        self.assertFalse(second.invoiceitems_set.exists())
        self.assertEqual((second.total, second.final_total), (0, 0))

    def test_editing_an_item_on_its_own_page_updates_the_invoice(self):
        self.post_invoice()
        item = InvoiceItems.objects.get()
        response = self.client.post("/accounts/mastersheet/invoiceitems/%d/change/" % item.id, {
            "invoice": item.invoice_id, "material_type": self.material.id, "phase": "1", "slum": self.slum.id,
            "household_numbers": '["101", "102", "103"]', "quantity": "10", "unit": "2", "rate": "100",
            "tax": "0", "total": "-1",
        })
        self.assertEqual(response.status_code, 302, response.content[:2000])
        invoice = Invoice.objects.get()
        self.assertEqual((InvoiceItems.objects.get().total, invoice.total, invoice.final_total), (3000.0, 3000.0, 3000.0))


class SponsorFundTests(FinanceCase):
    def post_project(self, name, funds="1000", used=""):
        return self.client.post(PROJECT_URL, {
            "name": name, "project_type": "1", "funds_sponsored": funds, "funds_utilised": used, "status": "2",
            "projectdocuments_set-TOTAL_FORMS": "0", "projectdocuments_set-INITIAL_FORMS": "0",
            "projectdocuments_set-MIN_NUM_FORMS": "0", "projectdocuments_set-MAX_NUM_FORMS": "1000",
            "projectimages_set-TOTAL_FORMS": "0", "projectimages_set-INITIAL_FORMS": "0",
            "projectimages_set-MIN_NUM_FORMS": "0", "projectimages_set-MAX_NUM_FORMS": "1000",
        })

    def test_negative_funds_are_refused(self):
        self.assertEqual(self.post_project("Neg sponsored", funds="-5000").status_code, 200)
        self.assertEqual(self.post_project("Neg used", used="-4000000").status_code, 200)
        self.assertFalse(SponsorProject.objects.filter(name__startswith="Neg").exists())

    def test_valid_funds_are_saved(self):
        self.assertEqual(self.post_project("Good", funds="1000.50", used="0").status_code, 302)
        self.assertTrue(SponsorProject.objects.filter(name="Good").exists())


class ComponentMetricTests(TestCase):
    def test_negative_metric_is_refused_by_the_kml_form(self):
        from django.core.exceptions import ValidationError
        from component.forms import KMLUpload
        with self.assertRaises(ValidationError):
            KMLUpload.base_fields["metric_value"].clean("-5")
        self.assertEqual(str(KMLUpload.base_fields["metric_value"].clean("12.5")), "12.5")
