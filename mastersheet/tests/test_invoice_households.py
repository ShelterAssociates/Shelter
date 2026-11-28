"""A stored invoice item whose household list is not a list (a tampered request) breaks no report or save."""

import json

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from mastersheet.models import InvoiceItems, household_list
from mastersheet.tests.test_financial_values import FinanceCase


class TamperedHouseholdsTests(FinanceCase):
    def setUp(self):
        super().setUp()
        Group.objects.create(name="city:Thane")
        self.assertEqual(self.post_invoice(number="VAXSS1").status_code, 302)
        self.item = InvoiceItems.objects.get(invoice__invoice_number="VAXSS1")
        InvoiceItems.objects.filter(pk=self.item.pk).update(household_numbers=1)

    def test_accounts_report_still_loads(self):
        body = {"tag": "slum", "keys": [self.slum.id], "startDate": None, "endDate": None}
        response = self.client.post("/mastersheet/report_table_accounts/", json.dumps(body),
                                    content_type="application/json", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)

    def test_new_invoice_for_the_same_slum_can_be_saved(self):
        self.assertEqual(self.post_invoice(number="INV-2", households='["103"]').status_code, 302)
        self.assertTrue(InvoiceItems.objects.filter(invoice__invoice_number="INV-2").exists())

    def test_a_household_value_that_is_not_a_list_is_refused_on_save(self):
        self.item.household_numbers = 1
        with self.assertRaises(ValidationError):
            self.item.save()

    def test_only_lists_count_as_households(self):
        self.assertEqual([household_list(v) for v in (["101"], 1, "101", None)], [["101"], [], [], []])
