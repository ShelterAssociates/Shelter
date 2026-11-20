from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, FileResponse, Http404
from sponsor.models import *
from master.models import *
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils.text import slugify
from sponsor.forms import SERVED_DOCUMENT_EXTENSIONS, SERVED_IMAGE_EXTENSIONS
from utils.uploads import file_extension

import json
from component.cipher import *
from sponsor.birt_ff_report import build_command, report_exec
import zipfile
import shutil
import os
import tempfile


@login_required(login_url="/accounts/login/")
def sponsors(request):

    cipher = AESCipher()

    # -----------------------------
    # Sponsor projects (ordered)
    # -----------------------------
    sponsor_loggedin = SponsorProject.objects.filter(
        sponsor__user=request.user
    ).order_by("-start_date")

    # -----------------------------
    # Slums under sponsor
    # -----------------------------
    slums_under_sponsor = SponsorProjectDetails.objects.filter(
        sponsor__user=request.user
    )

    slums_under_sponsor_array = []

    for i in slums_under_sponsor:
        slums_under_sponsor_dict = {
            "name": i.slum.name,
            "households": i.household_code,
            "project_of_slum": i.sponsor_project,
            "no_of_households": len(i.household_code),
            "slum_id": i.slum.id,
            "cityname": str(
                i.slum.electoral_ward.administrative_ward.city.name.city_name
            ),
            "city_id": i.slum.electoral_ward.administrative_ward.city.id,
            "city_id_encrypted": "city::"
            + str(
                cipher.encrypt(str(i.slum.electoral_ward.administrative_ward.city.id))
            ),
            "subfields": i.sponsorprojectdetailssubfields_set.all(),
        }
        slums_under_sponsor_array.append(slums_under_sponsor_dict)

    slums_under_sponsor_array = sorted(
        slums_under_sponsor_array, key=lambda k: k["cityname"]
    )

    # -----------------------------
    # Build projects data
    # -----------------------------
    projects_under_sponsor_array = []

    for l in sponsor_loggedin:

        no_of_households = 0
        no_of_households_q1 = 0
        no_of_households_q2 = 0
        no_of_households_q3 = 0
        no_of_households_q4 = 0

        tempArray = []

        for m in slums_under_sponsor_array:
            if str(l.name) == str(m["project_of_slum"]):
                no_of_households += m["no_of_households"]
                tempArray.append(m)

        # -----------------------------
        # VALIDATE IMAGES (KEY FIX)
        # -----------------------------
        all_images = ProjectImages.objects.filter(sponsor_project__name=l.name)

        valid_images = []
        for img in all_images:
            if img.image and default_storage.exists(img.image.name):
                valid_images.append(img)

        # -----------------------------
        # Documents
        # -----------------------------
        docs = ProjectDocuments.objects.filter(sponsor_project__name=l.name)

        projects_under_sponsor_dict = {
            "project_Name": l.name,
            "project_Type": l.project_type,
            "start_year": l.start_date,
            "end_year": l.end_date,
            "status": l.status,
            "q1_households": no_of_households_q1,
            "q2_households": no_of_households_q2,
            "q3_households": no_of_households_q3,
            "q4_households": no_of_households_q4,
            "images": valid_images,  # ✅ only existing images
            "documents": docs,
            "slums_in_project": tempArray,
            "households_in_project": no_of_households,
        }

        projects_under_sponsor_array.append(projects_under_sponsor_dict)

    # -----------------------------
    # Render
    # -----------------------------
    return render(request, "sponsors.html", {"projects": projects_under_sponsor_array})


PROJECT_FILES = {
    "document": (ProjectDocuments, "document", SERVED_DOCUMENT_EXTENSIONS),
    "image": (ProjectImages, "image", SERVED_IMAGE_EXTENSIONS),
}
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "jfif": "image/jpeg",
    "png": "image/png",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@login_required(login_url="/accounts/login/")
def project_file(request, kind, pk):
    model, field, allowed = PROJECT_FILES[kind]
    obj = get_object_or_404(model.objects.select_related("sponsor_project__sponsor"), pk=pk)
    sponsor = obj.sponsor_project.sponsor
    if not (request.user.is_staff or (sponsor and sponsor.user_id == request.user.id)):
        raise Http404
    stored = getattr(obj, field)
    ext = file_extension(stored.name)
    if ext not in allowed or not stored.storage.exists(stored.name):
        raise Http404
    handle = stored.open("rb")
    if ext == "pdf" and b"%PDF-" not in handle.read(1024):
        handle.close()
        raise Http404
    handle.seek(0)
    response = FileResponse(
        handle,
        as_attachment=kind == "document",
        filename=os.path.basename(stored.name),
        content_type=CONTENT_TYPES[ext],
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response["Cache-Control"] = "private, no-store"
    return response


def _private(response):
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required(login_url="/accounts/login/")
def ff_report_zip(request, pk):
    """Household factsheet ZIP of one sponsored slum: staff, or the sponsor that owns it (VAPT #6)."""
    sub = get_object_or_404(
        SponsorProjectDetailsSubFields.objects.select_related("sponsor_project_details__sponsor"), pk=pk
    )
    if not (request.user.is_staff or sub.sponsor_project_details.sponsor.user_id == request.user.id):
        raise Http404
    stored = sub.zip_file
    if not stored or file_extension(stored.name) != "zip" or not stored.storage.exists(stored.name):
        raise Http404
    return _private(FileResponse(
        stored.open("rb"), as_attachment=True, filename=os.path.basename(stored.name), content_type="application/zip"
    ))


@login_required(login_url="/accounts/login/")
def create_zip(request, slumname):
    """Builds the household factsheet PDFs of one of the sponsor's slums in a throwaway folder."""
    details = (
        SponsorProjectDetails.objects.filter(sponsor__user=request.user, slum__name=slumname)
        .select_related("slum")
        .first()
    )
    if details is None:
        raise Http404
    cipher = AESCipher()
    slum_code = str(details.slum.shelter_slum_code)
    with tempfile.TemporaryDirectory() as workdir:
        folder = os.path.join(workdir, "households")
        os.mkdir(folder)
        for household_code in details.household_code or []:
            key = cipher.encrypt("%s|%s|%s" % (slum_code, household_code, request.user.id))
            pdf_file = os.path.join(folder, "household_code_{}.pdf".format(household_code))
            report_exec(build_command(settings.BIRT_REPORT_CMD, pdf_file, key))
        with open(shutil.make_archive(folder, "zip", folder), "rb") as archive:
            content = archive.read()
    response = HttpResponse(content, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="%s.zip"' % (slugify(slumname) or "households")
    return _private(response)
