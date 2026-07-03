#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django tests page for master app"""

from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from unittest.mock import MagicMock, Mock, patch

from master.views import filterMasterList, rimdisplay


class RimDisplayFilterTests(TestCase):
	def setUp(self):
		self.factory = RequestFactory()

	@patch("master.views.render")
	@patch("master.views.Paginator")
	@patch("master.views.Rapid_Slum_Appraisal")
	def test_rimdisplay_applies_hierarchical_filters_and_text_search(
		self, mock_model, mock_paginator, mock_render
	):
		queryset = MagicMock()
		queryset.select_related.return_value = queryset
		queryset.all.return_value = queryset
		queryset.filter.return_value = queryset
		queryset.order_by.return_value = queryset
		mock_model.objects.select_related.return_value = queryset

		page = MagicMock()
		page.paginator.count = 1
		page.paginator.num_pages = 1
		page.number = 1
		page.__iter__.return_value = iter([])
		mock_paginator.return_value.page.return_value = page
		mock_render.return_value = HttpResponse("ok")

		request = self.factory.get(
			"/sluminformation/rim/display/",
			{
				"q": "alpha",
				"city": "10",
				"admin": "11",
				"electoral": "12",
				"slum": "13",
			},
		)

		rimdisplay(request)

		queryset.filter.assert_any_call(slum_name__electoral_ward__administrative_ward__city_id="10")
		queryset.filter.assert_any_call(slum_name__electoral_ward__administrative_ward_id="11")
		queryset.filter.assert_any_call(slum_name__electoral_ward_id="12")
		queryset.filter.assert_any_call(slum_name_id="13")
		queryset.filter.assert_any_call(slum_name__name__icontains="alpha")

		context = mock_render.call_args[0][2]
		self.assertIn("RA", context)
		self.assertIn("R", context)

	@patch("master.views.Slum")
	@patch("master.views.ElectoralWard")
	@patch("master.views.AdministrativeWard")
	@patch("master.views.City")
 
	def test_filter_master_list_uses_expected_parent_parameters(
		self, mock_city, mock_admin, mock_electoral, mock_slum
	):
		city_queryset = MagicMock()
		city_queryset.order_by.return_value = city_queryset
		city_record = Mock(id=1, name="City A")
		city_queryset.__iter__.return_value = iter([city_record])
		mock_city.objects.all.return_value = city_queryset

		admin_queryset = MagicMock()
		admin_queryset.filter.return_value = admin_queryset
		admin_queryset.order_by.return_value = admin_queryset
		admin_record = Mock(id=2, name="Ward A")
		admin_queryset.__iter__.return_value = iter([admin_record])
		mock_admin.objects.all.return_value = admin_queryset

		electoral_queryset = MagicMock()
		electoral_queryset.filter.return_value = electoral_queryset
		electoral_queryset.order_by.return_value = electoral_queryset
		electoral_record = Mock(id=3, name="Electoral A")
		electoral_queryset.__iter__.return_value = iter([electoral_record])
		mock_electoral.objects.all.return_value = electoral_queryset

		slum_queryset = MagicMock()
		slum_queryset.filter.return_value = slum_queryset
		slum_queryset.order_by.return_value = slum_queryset
		slum_record = Mock(id=4, name="Slum A")
		slum_queryset.__iter__.return_value = iter([slum_record])
		mock_slum.objects.all.return_value = slum_queryset

		request = self.factory.post("/filterMasterList/", {"type": "slum", "electoral": "7"})
		response = filterMasterList(request)

		self.assertEqual(response.status_code, 200)
		slum_queryset.filter.assert_called_with(electoral_ward_id="7")
