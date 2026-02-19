import json
from turtle import mode

import requests
import time

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from master.models import Slum, Rapid_Slum_Appraisal
from .services.rim_factsheet import get_rim_factsheet_detail, resolve_rim_images,map_rim_data
from pprint import pprint
from datetime import date
from django.core.cache import cache

PDF_SERVICE_URL = "https://shelter-associates.org/pdf/generate-pdf"
PDF_SECRET_KEY = "RIM_PDF_2025"
PDF_SERVICE_URL_LOCAL = "http://127.0.0.1:9000/generate-pdf"
PDF_SERVICE_URL_LOCAL_FETCH = "http://127.0.0.1:9000/fetch-pdf"  # for dockerized version


def report_view(request):
    context = {}

    if request.method == "POST":
        slum_id = request.POST.get("slum_id")

        factsheet_context = rim_factsheet_view(slum_id)

        if factsheet_context.get("meta_data", {}).get("_exists"):
            context["factsheet"] = factsheet_context

    return render(request, "reports/rim_factsheet/report_home.html", context)  

def rim_factsheet_html_report(request, slum_id):
    """
    HTML preview for RIM Factsheet
    (Same data + same template as PDF)
    """
    context = rim_factsheet_view(slum_id)
    if not context.get("meta_data", {}).get("_exists"):

        return HttpResponse("Slum not found", status=404)


    return render(
        request,
        "reports/rim_factsheet/full_page/factsheet.html",
        context
    )





def rim_factsheet_pdf_generation(request, slum_id):
	force_generate = request.GET.get("force_generate", "false").lower() == "true"
	print(f"force_generate is : {force_generate}")
	cache_key = f"rim_context_{slum_id}"
	context = cache.get(cache_key)
	if context is None:
		print("⚡ Running heavy calculation...")
		context = rim_factsheet_view(slum_id)
		cache.set(cache_key, context, timeout=120)
	else:
		print("⚡ Using cached context...")

	
	if context.get("data") == "NA":
		return HttpResponse("No data available for PDF generation", status=405)
	elif context.get("meta_data", {}).get("_exists") == False:
		return HttpResponse("Slum not found", status=406)
			
	html = render_to_string("reports/rim_factsheet/pdf/factsheet_pdf.html", context)

	try:
		resp = requests.post(
			PDF_SERVICE_URL_LOCAL,
			headers={"X-PDF-KEY": PDF_SECRET_KEY},
			json={
				"html": html,
				"slum_id": slum_id,
				"force_generate": force_generate,
			},
			timeout=120  # waits until PDF is generated & saved
		)

		if resp.status_code == 200:
			return HttpResponse(
				"PDF generated and saved successfully",
				status=202
			)

		return HttpResponse(
			"PDF generation failed",
			status=500
		)

	except requests.exceptions.Timeout:
		return HttpResponse(
			"PDF generation timed out",
			status=504
		)

def rim_factsheet_preview(request, slum_id):
	"""
	Endpoint to preview the generated PDF in browser
	"""
	cache_key = f"rim_context_{slum_id}"
	context = cache.get(cache_key)
	if context is None:
		print("⚡ Running heavy calculation...")
		context = rim_factsheet_view(slum_id)
		cache.set(cache_key, context, timeout=120)
	else:
		print("⚡ Using cached context...")
	if context.get("data") == "NA":
		return HttpResponse("No data available for PDF generation", status=404)
	elif context.get("meta_data", {}).get("_exists") == False:
		return HttpResponse("Slum not found", status=404)
			
	html = render_to_string("reports/rim_factsheet/preview/factsheet_preview.html", context)

	return HttpResponse(html)  # For simplicity, directly returning HTML for preview


def rim_factsheet_pdf_fetch(request, slum_id):
	"""
	Fetches the generated PDF and forces browser download
	"""

	try:
		resp = requests.get(
			f"{PDF_SERVICE_URL_LOCAL_FETCH}?slum_id={slum_id}",
			headers={"X-PDF-KEY": PDF_SECRET_KEY},
			timeout=30
		)

		if resp.status_code == 200:
			response = HttpResponse(
				resp.content,
				content_type="application/pdf"
			)

			# 🔥 FORCE DOWNLOAD (key line)
			response["Content-Disposition"] = (
				f'attachment; filename="rim_factsheet_{slum_id}.pdf"'
			)

			# Optional but recommended
			response["Content-Length"] = len(resp.content)

			return response

		return HttpResponse("PDF not ready", status=404)

	except requests.exceptions.Timeout:
		return HttpResponse("PDF fetch timed out", status=504)

	

def rim_factsheet_view(slum_id, raw=False):
	"""
	API endpoint for RIM factsheet JSON.
	"""
	slum_id = int(slum_id)
	response = {
		"status": False,
		"image": False,
		"_exists": False
	}

	slum = Slum.objects.filter(id=slum_id).first()
	if not slum:
		return response

	response["_exists"] = True
	response.update(get_rim_factsheet_detail(slum_id))
	if response.get("data") == "NA":
		return response
	
	response["status"] = len(response) > 2

	response.update({
		"city_name": slum.electoral_ward.administrative_ward.city.name.city_name,
		"admin_ward": slum.electoral_ward.administrative_ward.name,
		"electoral_ward": slum.electoral_ward.name,
		"slum_name": slum.name,
	})

	rim_image = Rapid_Slum_Appraisal.objects.filter(
		slum_name=slum
	).values().first()
	if not rim_image:
		response["_exists"] = False
		return response

	if rim_image:
		if response.get("number_of_community_toilet_blo") == 0:
			rim_image.pop("toilet_seat_to_persons_ratio", None)
			rim_image.pop("toilet_cost", None)

		response.update(resolve_rim_images(rim_image))
		response["image"] = True



	return map_rim_data(response)