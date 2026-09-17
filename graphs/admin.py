from django import forms
from django.conf import settings
from django.contrib import admin
from django.db.models import Q
from django.http import JsonResponse
from django.urls import path
from .models import *
import datetime
from django.contrib.auth.models import User
from master.models import Slum

SLUM_FILTER_PARAM = "slum__id__in"


class HouseholdDataAdmin(admin.ModelAdmin):
    change_list_template = "admin/graphs/householddata/change_list.html"
    list_filter = ["slum__electoral_ward__administrative_ward__city"]
    list_display = (
        "household_number",
        "ff_data",
        "rhs_data",
        "slum",
        "created_date",
        "submission_date",
    )
    search_fields = ["household_number", "slum__name", "=slum__id"]
    ordering = ["slum", "household_number"]
    raw_id_fields = ["slum"]
    list_per_page = 10

    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        return super().media + forms.Media(
            css={"all": ("admin/css/vendor/select2/select2%s.css" % extra, "admin/css/autocomplete.css")},
            js=(
                "admin/js/vendor/jquery/jquery%s.js" % extra,
                "admin/js/vendor/select2/select2.full%s.js" % extra,
                "admin/js/jquery.init.js",
                "graphs/householddata_slum_filter.js",
            ),
        )

    def get_urls(self):
        urls = [
            path(
                "slum-search/",
                self.admin_site.admin_view(self.slum_search),
                name="graphs_householddata_slum_search",
            )
        ]
        return urls + super().get_urls()

    def slum_search(self, request):
        """JSON for the changelist slum picker: matches slum name (contains) or exact slum id."""
        term = request.GET.get("term", "").strip()
        qs = Slum.objects.all()
        if term:
            cond = Q(name__icontains=term)
            if term.isdigit():
                cond |= Q(id=int(term))
            qs = qs.filter(cond)
        results = [{"id": s.id, "text": "%s (%s)" % (s.name, s.id)} for s in qs.order_by("name")[:20]]
        return JsonResponse({"results": results})

    def changelist_view(self, request, extra_context=None):
        raw = request.GET.get(SLUM_FILTER_PARAM, "")
        ids = [i for i in raw.split(",") if i.isdigit()]
        if not ids and SLUM_FILTER_PARAM in request.GET:
            request.GET = request.GET.copy()
            del request.GET[SLUM_FILTER_PARAM]
        extra_context = dict(
            extra_context or {},
            slum_filter_param=SLUM_FILTER_PARAM,
            slum_filter_value=raw,
            selected_slums=Slum.objects.filter(id__in=ids).order_by("name"),
        )
        return super().changelist_view(request, extra_context)


admin.site.register(HouseholdData, HouseholdDataAdmin)


class FollowupDataAdmin(admin.ModelAdmin):
    list_filter = ["slum__electoral_ward__administrative_ward__city"]
    list_display = (
        "household_number",
        "slum",
        "followup_data",
        "created_date",
        "submission_date",
        "flag_followup_in_rhs",
    )
    search_fields = ["household_number", "slum_id__name"]
    ordering = ["slum", "household_number"]
    raw_id_fields = ["slum"]
    list_per_page = 10


admin.site.register(FollowupData, FollowupDataAdmin)


class RIMDataAdmin(admin.ModelAdmin):
    list_filter = ["slum__electoral_ward__administrative_ward__city"]
    list_display = ("rim_data", "slum", "created_on", "submission_date")
    search_fields = ["slum_id__name"]
    ordering = ["slum"]
    raw_id_fields = ["slum"]
    list_per_page = 5


admin.site.register(SlumData, RIMDataAdmin)


class CovidDataAdmin(admin.ModelAdmin):
    list_filter = ["slum__electoral_ward__administrative_ward__city", "date_of_survey"]
    list_display = (
        "household_number",
        "family_member_name",
        "covid_uuid",
        "slum",
        "date_of_survey",
        "last_modified_date",
    )
    search_fields = ["slum_id__name", "household_number"]
    ordering = ["slum", "household_number"]
    raw_id_fields = ["slum"]
    list_per_page = 10


admin.site.register(CovidData, CovidDataAdmin)


@admin.register(MemberData)
class MemberDataAdmin(admin.ModelAdmin):
    list_filter = ["slum__electoral_ward__administrative_ward__city"]
    list_display = (
        "member_first_name",
        "member_uuid",
        "slum",
        "created_date",
        "submission_date",
    )
    search_fields = ["slum_id__name"]
    raw_id_fields = ["slum"]
    list_per_page = 10


# admin.site.register(MemberData, MemberDataAdmin)

# admin.site.register(GroupData, GroupDataAdmin)
