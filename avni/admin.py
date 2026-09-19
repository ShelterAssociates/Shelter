from django.contrib import admin

from .models import AvniForm, AvniFormMapping, AvniFormQuestion, AvniMapFilter


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
    actions = ["show_on_map"]

    def has_add_permission(self, request):
        return False

    def show_on_map(self, request, queryset):
        coded = queryset.filter(data_type="Coded").exclude(concept_uuid="")
        created = 0
        for question in coded.order_by("display_order"):
            _, was_created = AvniMapFilter.objects.get_or_create(
                concept_uuid=question.concept_uuid, defaults={"question": question, "order": question.display_order}
            )
            created += was_created
        skipped = queryset.count() - coded.count()
        self.message_user(request, "{} map filter(s) added, {} already present, {} skipped (not coded).".format(
            created, coded.count() - created, skipped))

    show_on_map.short_description = "Show selected concepts as map filters"
    show_on_map.allowed_permissions = ("map_filter",)

    def has_map_filter_permission(self, request):
        return request.user.has_perm("avni.add_avnimapfilter")


@admin.register(AvniMapFilter)
class AvniMapFilterAdmin(admin.ModelAdmin):
    list_display = ("concept_name", "form_name", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("concept_name", "concept_uuid")
    autocomplete_fields = ("question",)
    fields = ("question", "order", "is_active", "concept_uuid")
    readonly_fields = ("concept_uuid",)

    def form_name(self, map_filter):
        return map_filter.question.form.name
