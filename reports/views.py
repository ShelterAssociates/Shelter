import json
from turtle import mode
import requests
import time
from django.templatetags.static import static
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.template.loader import render_to_string
from django.conf import settings
from .services.rim_factsheet import rim_factsheet_view
from django.core.cache import cache
from django.http import JsonResponse
from reports.models import SponsorProjectMonthlyReportDetails , SponsorProjectReportDetails
from reports.services.monthly_report_service import monthly_report_details



def report_view(request):
    context = {}

    if request.method == "POST":
        slum_id = request.POST.get("slum_id")

        factsheet_context = rim_factsheet_view(slum_id)

        if factsheet_context.get("meta_data", {}).get("_exists"):
            context["factsheet"] = factsheet_context

    return render(request, "report_home.html", context)  

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
	cache_key = f"rim_context_{slum_id}"
	context = cache.get(cache_key)
	if context is None:
		context = rim_factsheet_view(slum_id)
		cache.set(cache_key, context, timeout=120)

	if context.get("data") == "NA":
		return HttpResponse("No data available for PDF generation", status=405)
	elif context.get("meta_data", {}).get("_exists") == False:
		return HttpResponse("Slum not found", status=406)
			
	html = render_to_string("reports/rim_factsheet/pdf/factsheet_pdf.html", context)
	try:
		resp = requests.post(
			settings.PDF_SERVICE_URL,
			headers={"X-PDF-KEY": settings.PDF_SECRET_KEY},
			json={
				"html": html,
				"report_id": slum_id,
				"file_name": f"RIM_Factsheet_{context.get('meta_data',{}).get('city_name','City').replace(' ','_').replace('/','_')}_{context.get('meta_data',{}).get('slum_name','Slum').replace(' ','_').replace('/','_')}",	
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
		context = rim_factsheet_view(slum_id)
		cache.set(cache_key, context, timeout=120)


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
		if not request.session.get("rim_otp_verified"):
			return HttpResponseForbidden("OTP verification required")
		resp = requests.get(
			f"{settings.PDF_FETCH_URL}?report_id={slum_id}&report_type=rim_factsheet",
			headers={"X-PDF-KEY": settings.PDF_SECRET_KEY},
			timeout=30
		)

		if resp.status_code == 200:
			response = HttpResponse(
				resp.content,
				content_type="application/pdf",

			)

			# 🔥 FORCE DOWNLOAD (key line)
			content_disposition = resp.headers.get("Content-Disposition")

			if content_disposition:
				response["Content-Disposition"] = content_disposition
			else:
				response["Content-Disposition"] = f'attachment; filename="report_{slum_id}.pdf"'

			# Optional but recommended
			response["Content-Length"] = len(resp.content)
			request.session["rim_otp_verified"] = False
			return response

		return HttpResponse("PDF not ready", status=404)

	except requests.exceptions.Timeout:
		return HttpResponse("PDF fetch timed out", status=504)

	


# ================ Donar report =============================


def monthly_donor_report_pdf_generation(request, report_id):
	
	cache_key = f"monthly_report_{report_id}"
	context = cache.get(cache_key)

	if context is None:
		data = monthly_report_details(request,report_id)
		context = {
			"data": data,
			"base_url": request.build_absolute_uri("/")[:-1]
		}
		cache.set(cache_key, context, timeout=120)
	if not context.get("data"):
		return HttpResponse("No data available for PDF generation", status=405)
	html = render_to_string(
		"reports/donor_report/monthly_report_pdf.html",
		context
	)
	data = context.get("data")
	try:
		resp = requests.post(
			settings.PDF_SERVICE_URL,
			headers={"X-PDF-KEY": settings.PDF_SECRET_KEY},
			json={
				"html": html,
				"report_id": report_id,
				"file_name": f"Donor_Monthly_Report_{data['project']['sponsor_name'].replace(' ', '_')}_{data['month'].replace(' ', '_')}",
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

		return HttpResponse(query_rim_factsheet_data, 
			"PDF generation failed",
			status=500
		)

	except requests.exceptions.Timeout:
		return HttpResponse(
			"PDF generation timed out",
			status=504
		)

def monthly_donor_report_pdf_fetch(request, report_id):
	
	try:
		resp = requests.get(
			f"{settings.PDF_FETCH_URL}?report_id={report_id}&report_type=donor_report",
			headers={"X-PDF-KEY": settings.PDF_SECRET_KEY},
			timeout=30
		)
		if resp.status_code == 200:
			response = HttpResponse(
				resp.content,
				content_type="application/pdf"
			)
			content_disposition = resp.headers.get("Content-Disposition")

			if content_disposition:
				response["Content-Disposition"] = content_disposition
			else:
				response["Content-Disposition"] = f'attachment; filename="report_{report_id}.pdf"'

			response["Content-Length"] = len(resp.content)

			return response

		return HttpResponse("PDF not ready", status=404)

	except requests.exceptions.Timeout:
		return HttpResponse("PDF fetch timed out", status=504)

def donor_projects(request):

	projects = SponsorProjectReportDetails.objects.select_related(
		"sponsor_project"
	).all()

	data = []

	for project in projects:
		data.append({
			"id": project.id,
			"name": str(project.sponsor_project)
		})

	return JsonResponse({
		"projects": data
	})

def project_months(request, project_id):

	monthly_reports = SponsorProjectMonthlyReportDetails.objects.filter(
		project_report_id=project_id,
		status="completed"
	).order_by("month")

	data = []

	for report in monthly_reports:
		data.append({
			"id": report.id,
			"month": report.month.strftime("%B %Y")
		})

	return JsonResponse({
		"months": data
	})