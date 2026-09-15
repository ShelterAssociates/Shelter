from django.contrib import admin

from .models import AvniForm, AvniFormMapping, AvniFormQuestion


class AvniFormMappingInline(admin.TabularInline):
    model = AvniFormMapping
    extra = 0
    can_delete = False
    readonly_fields = ("uuid", "subject_type", "program", "encounter_type", "is_active")


@admin.register(AvniForm)
class AvniFormAdmin(admin.ModelAdmin):
    list_display = ("name", "form_type", "is_active", "fetched_on", "question_count")
    list_filter = ("form_type", "is_active")
    search_fields = ("name", "uuid")
    readonly_fields = ("uuid", "name", "form_type", "fetched_on", "is_active", "definition")
    inlines = [AvniFormMappingInline]

    def has_add_permission(self, request):
        return False

    def question_count(self, form):
        return form.questions.filter(is_active=True).count()


@admin.register(AvniFormQuestion)
class AvniFormQuestionAdmin(admin.ModelAdmin):
    list_display = ("question_name", "concept_name", "data_type", "is_multi_select", "is_mandatory", "form", "is_active")
    list_filter = ("data_type", "is_active", "form")
    search_fields = ("question_name", "concept_name", "concept_uuid")
    readonly_fields = tuple(f.name for f in AvniFormQuestion._meta.fields)

    def has_add_permission(self, request):
        return False
