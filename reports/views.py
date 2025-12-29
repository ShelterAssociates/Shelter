import json


from django.http import HttpResponse
from django.shortcuts import render

from master.models import Slum, Rapid_Slum_Appraisal
from .services.rim_factsheet import get_rim_factsheet_detail, resolve_rim_images,map_rim_data
from pprint import pprint
from datetime import date

def rim_factsheet_html_view(request, slum_id):
	factsheet = rim_factsheet_view(slum_id)
	# pprint(factsheet)
	return render(request, "reports/factsheet.html", factsheet)


def rim_factsheet_view(slum_id, raw=False):
	"""
	API endpoint for RIM factsheet JSON.
	"""
	slum_id = int(slum_id)
	response = {
		"status": False,
		"image": False
	}

	slum = Slum.objects.filter(id=slum_id).first()
	if not slum:
		return HttpResponse(json.dumps(response), content_type="application/json")

	response.update(get_rim_factsheet_detail(slum_id))
	response["status"] = len(response) > 2

	response.update({
		"city_name": slum.electoral_ward.administrative_ward.city.name.city_name,
		"admin_ward": slum.electoral_ward.administrative_ward.name,
		"electoral_ward": slum.electoral_ward.name,
		"slum_name": slum.name,
	})
	print(response)
	rim_image = Rapid_Slum_Appraisal.objects.filter(
		slum_name=slum
	).values().first()

	if rim_image:
		if response.get("number_of_community_toilet_blo") == 0:
			rim_image.pop("toilet_seat_to_persons_ratio", None)
			rim_image.pop("toilet_cost", None)

		response.update(resolve_rim_images(rim_image))
		response["image"] = True
	return map_rim_data(response) 