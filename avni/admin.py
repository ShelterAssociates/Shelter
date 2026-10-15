from django.contrib import admin

from .models import (
    AvniFilterPreset,
    AvniFilterPresetItem,
    AvniFilterPresetScope,
    AvniForm,
    AvniFormMapping,
    AvniFormQuestion,
    AvniMapFilter,
    AvniStageFilter,
)


class AvniFormMappingInline(admin.TabularInline):
    model = AvniFormMapping
    extra = 0
    can_delete = False
    readonly_fields = ("uuid", "subject_type", "program", "encounter_type", "is_active")


@admin.register(AvniForm)
class AvniFormAdmin(admin.ModelAdmin):
    list_display = ("name", "form_type", "shows_map", "is_active", "fetched_on", "question_count")
    list_editable = ("shows_map",)
    list_filter = ("form_type", "shows_map", "is_active")
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


@admin.register(AvniFormMapping)
class AvniFormMappingAdmin(admin.ModelAdmin):
    """Read-only catalog of the synced forms; the preset screens pick from here."""

    list_display = ("subject_type", "program", "encounter_type", "form", "is_active")
    list_filter = ("subject_type", "program", "is_active", "form__form_type")
    search_fields = ("subject_type", "program", "encounter_type", "form__name")
    readonly_fields = tuple(f.name for f in AvniFormMapping._meta.fields)

    def has_add_permission(self, request):
        return False


class AvniStageFilterInline(admin.TabularInline):
    model = AvniStageFilter
    extra = 0
    autocomplete_fields = ("question",)


class AvniFilterPresetItemInline(admin.TabularInline):
    model = AvniFilterPresetItem
    fk_name = "preset"
    extra = 0
    autocomplete_fields = ("mapping", "anchor_question")
    raw_id_fields = ("pairs_with",)
    fields = ("mapping", "label", "show_as_filter", "is_required", "anchor_question", "rollup",
              "pairs_with", "default_window", "filled_color", "absent_color", "order")


class AvniFilterPresetScopeInline(admin.TabularInline):
    model = AvniFilterPresetScope
    extra = 0
    raw_id_fields = ("city", "slum")
    verbose_name_plural = "Scopes (a city row covers every slum of that city)"


@admin.register(AvniFilterPreset)
class AvniFilterPresetAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "is_active", "form_count", "required_count", "created_on")
    list_filter = ("is_active",)
    search_fields = ("name", "notes")
    autocomplete_fields = ("occupancy_question",)
    inlines = [AvniFilterPresetItemInline, AvniFilterPresetScopeInline]
    actions = ["copy_as_next_version"]

    def form_count(self, preset):
        return preset.items.count()

    def required_count(self, preset):
        return preset.items.filter(is_required=True).count()

    def copy_as_next_version(self, request, queryset):
        for preset in queryset:
            highest = AvniFilterPreset.objects.filter(name=preset.name).order_by("-version").first()
            copy = AvniFilterPreset.objects.create(
                name=preset.name, version=highest.version + 1, is_active=False, notes=preset.notes)
            # pairs_with points inside the preset, so the copies are linked after every item exists.
            new_items = {}
            for item in preset.items.all():
                original_id, original_pair = item.id, item.pairs_with_id
                item.pk, item.preset = None, copy
                item.save()
                new_items[original_id] = (item, original_pair)
            for item, original_pair in new_items.values():
                if original_pair and original_pair in new_items:
                    item.pairs_with = new_items[original_pair][0]
                    item.save(update_fields=["pairs_with"])
            for original_id, (item, _) in new_items.items():
                for stage in AvniStageFilter.objects.filter(item_id=original_id):
                    stage.pk, stage.item = None, item
                    stage.save()
        self.message_user(request, "Copied {} preset(s) as a new, switched-off version.".format(queryset.count()))

    copy_as_next_version.short_description = "Copy as the next version (switched off)"


@admin.register(AvniFilterPresetItem)
class AvniFilterPresetItemAdmin(admin.ModelAdmin):
    """The screen for switching a form's filter on or off and marking it required."""

    list_display = ("display_label", "preset", "subject_type", "program", "encounter_type",
                    "show_as_filter", "is_required", "order")
    list_editable = ("show_as_filter", "is_required", "order")
    list_filter = ("preset", "show_as_filter", "is_required", "mapping__subject_type", "mapping__program")
    search_fields = ("label", "mapping__subject_type", "mapping__program", "mapping__encounter_type")
    autocomplete_fields = ("mapping", "anchor_question")
    raw_id_fields = ("pairs_with",)
    inlines = [AvniStageFilterInline]

    def get_queryset(self, request):
        return super(AvniFilterPresetItemAdmin, self).get_queryset(request).select_related(
            "preset", "mapping", "mapping__form")

    def subject_type(self, item):
        return item.mapping.subject_type

    def program(self, item):
        return item.mapping.program

    def encounter_type(self, item):
        return item.mapping.encounter_type
