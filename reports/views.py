import json

import requests
import time

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from master.models import Slum, Rapid_Slum_Appraisal
from .services.rim_factsheet import get_rim_factsheet_detail, resolve_rim_images,map_rim_data
from pprint import pprint
from datetime import date

import threading

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
        "reports/factsheet.html",
        context
    )


PDF_SERVICE_URL = "https://shelter-associates.org/pdf/generate-pdf"
PDF_SECRET_KEY = "RIM_PDF_2025"
PDF_SERVICE_URL_LOCAL = "http://127.0.0.1:9000/generate-pdf"

def trigger_full_pdf_generation(slum_id):
    def job():
        try:
            context = rim_factsheet_view(slum_id)
            context["pdf_mode"] = "full"

            html = render_to_string(
                "reports/factsheet_pdf.html",
                context
            )

            # Fire-and-forget (DO NOT read response)
            requests.post(
                PDF_SERVICE_URL_LOCAL,
                headers={"X-PDF-KEY": PDF_SECRET_KEY},
                json={
                    "html": html,
                    "slum_id": slum_id,
                    "mode": "full"
                },
                timeout=5
            )

            print("Full PDF prepared in background for", slum_id)

        except Exception as e:
            print("Background PDF error:", e)

    threading.Thread(target=job, daemon=True).start()



def rim_factsheet_pdf_proxy(request, slum_id):
    mode = request.GET.get("mode", "fast")  # fast | full

    # Prepare data
    context = rim_factsheet_view(slum_id)
    context["pdf_mode"] = mode

    html = render_to_string(
        "reports/factsheet_pdf.html",
        context
    )

    # Call PDF service
    resp = requests.post(
        PDF_SERVICE_URL_LOCAL,
        headers={"X-PDF-KEY": PDF_SECRET_KEY},
        json={
            "html": html,
            "slum_id": slum_id,
            "mode": mode
        },
        timeout=(5, 20 if mode == "fast" else 120)
    )

    # Background full PDF generation
    if mode == "fast":
        trigger_full_pdf_generation(slum_id)

    # Build response
    response = HttpResponse(
        resp.content,
        content_type="application/pdf"
    )

    # ---------- MODE HANDLING ----------
    if mode == "fast":
        # 🔒 FAST = preview only
        response["Content-Disposition"] = (
            "inline; filename=RIM_Factsheet_Preview.pdf"
        )

        # 🔄 Auto-upgrade ONCE
        if not request.GET.get("upgraded"):
            response["Refresh"] = "3; url=?mode=full&upgraded=1"

    elif mode == "full":
        # 👁 FULL = viewable, no forced download
        response["Content-Disposition"] = (
            "inline; filename=RIM_Factsheet_Full.pdf"
        )

    # ⬇ Explicit download only when asked
    if request.GET.get("download") == "1":
        response["Content-Disposition"] = (
            "attachment; filename=RIM_Factsheet_Full.pdf"
        )

    return response
	


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
	response["status"] = len(response) > 2
	# print(response)
	response.update({
		"city_name": slum.electoral_ward.administrative_ward.city.name.city_name,
		"admin_ward": slum.electoral_ward.administrative_ward.name,
		"electoral_ward": slum.electoral_ward.name,
		"slum_name": slum.name,
	})
	# print(response)
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