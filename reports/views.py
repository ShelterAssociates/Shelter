import json
from turtle import mode

import requests
import time
from django.templatetags.static import static

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from master.models import Slum, Rapid_Slum_Appraisal
from .services.rim_factsheet import get_rim_factsheet_detail, resolve_rim_images,map_rim_data
from pprint import pprint
from datetime import date
from django.core.cache import cache
from django.http import JsonResponse
from reports.models import SponsorProjectMonthlyReportDetails

PDF_SERVICE_URL = "https://shelter-associates.org/pdf/generate-pdf"
PDF_SECRET_KEY = "RIM_PDF_2025"
PDF_SERVICE_URL_LOCAL = "http://127.0.0.1:9000/generate-pdf"
PDF_SERVICE_URL_LOCAL_FETCH = "http://127.0.0.1:9000/fetch-pdf"  # for dockerized version

locations = {
	"Ganesh Nagar/ Pareira Nagar/Shastri Nagar" : "Shastri Nagar",
	"Waghhari Colony / Gholai Nagar" : "Gholai Nagar",
}

def format_location(name):
	return locations.get(name, name)

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
				"report_id": slum_id,
				"force_generate": force_generate,
				"report_type": "rim_factsheet",
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


## Donar report 
def donor_report_home(request):
	return render(request, "reports/donor_report/donor_report_home.html")


def monthly_report_details(request, report_id):

	report = SponsorProjectMonthlyReportDetails.objects.select_related(
		"project_report",
		"project_report__sponsor_project",
		"project_report__sponsor_project__sponsor"
	).prefetch_related(
		"project_report__project_locations",
		"project_report__project_deliverables__deliverable",
		"work_progress__location",
		"work_progress__parameter",
		"beneficiary_values__indicator",
		"deliverable_achievements__deliverable",
		"photos"
	).get(id=report_id)

	if report.status == "draft":
		return JsonResponse({
			"status": "draft",
			"message": "Please fill the data in monthly progress report and mark it completed."
		})

	project = report.project_report

	data = {
		"project": {
			"id": project.id,
			"name": str(project.sponsor_project),
			"sponsor_name": project.sponsor_project.sponsor.organization_name if project.sponsor_project.sponsor else None,
			"start_month": project.start_month.strftime("%b %Y") if project.start_month else None,
			"end_month": project.end_month.strftime("%b %Y") if project.end_month else None
		},
		"month": report.month.strftime("%b %Y") if report.month else None,
		"locations": [
			format_location(loc.name)
			for loc in project.project_locations.all()
		],
		"remarks": report.remarks
	}

	work_progress = {}

	for row in report.work_progress.all():
		loc = format_location(row.location.name)

		if loc not in work_progress:
			work_progress[loc] = []

		work_progress[loc].append({
			"parameter": row.parameter.name,
			"value": row.value
		})

	data["work_progress"] = [
		{"location": loc, "parameters": params}
		for loc, params in work_progress.items()
	]

	data["beneficiary_values"] = [
		{
			"indicator": row.indicator.name,
			"value": row.value,
			"icon": request.build_absolute_uri(row.indicator.icon.url) if row.indicator.icon else None
		}
		for row in report.beneficiary_values.all()
	]

	target_map = {
		d.deliverable_id: d
		for d in project.project_deliverables.all()
	}

	data["deliverables"] = []

	for r in report.deliverable_achievements.all():
		

		target_obj = target_map.get(r.deliverable_id)

		target_value = target_obj.target_value if target_obj else None
		unit = target_obj.unit if target_obj else None

		percent = round((r.value / target_value) * 100) if target_value else 0

		data["deliverables"].append({
			"deliverable": r.deliverable.name,
			"abbr": r.deliverable.abbrevation,
			"value": r.value,
			"target": target_value,
			"unit": unit,
			"icon": request.build_absolute_uri(r.deliverable.icon.url) if r.deliverable.icon else None,
			"percent": percent
		})

	data["photos"] = [
		{
			"image": request.build_absolute_uri(p.image.url) if p.image else None,
			"caption": p.caption
		}
		for p in report.photos.all()
	]

	return JsonResponse(data)


def monthly_report_pdf_generation(request, report_id):

	force_generate = True

	cache_key = f"monthly_report_{report_id}"
	context = cache.get(cache_key)

	if context is None:
		print("⚡ Fetching report data...")

		api_url = f"http://127.0.0.1:8000/reports/monthly-report/{report_id}/"
		response = requests.get(api_url)

		if response.status_code != 200:
			return HttpResponse("Failed to fetch report data", status=500)

		data = response.json()

		context = {
			"data": data,
			"base_url": request.build_absolute_uri("/")[:-1]
		}

		cache.set(cache_key, context, timeout=120)

	else:
		print("⚡ Using cached context...")

	if not context.get("data"):
		return HttpResponse("No data available for PDF generation", status=405)

	html = render_to_string(
		"reports/donor_report/monthly_report_pdf.html",
		context
	)

	try:
		resp = requests.post(
			PDF_SERVICE_URL_LOCAL,
			headers={"X-PDF-KEY": PDF_SECRET_KEY},
			json={
				"html": html,
				"report_id": report_id,
				"force_generate": True,
				"report_type": "donor_report"
			},
			timeout=120
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