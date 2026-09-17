"""Admin for the survey core: concepts (edit the SA text), records (read-only),
slum data versions, and the sync switches."""

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from survey import switches
from survey.models import Answer, Concept, ConceptAlias, Record, SlumDataVersion, SyncSwitch


class ConceptAliasInline(admin.TabularInline):
    model = ConceptAlias
    extra = 0
    can_delete = False
    readonly_fields = ("provider", "external_id", "external_name")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Concept)
class ConceptAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "sa_text", "data_type", "is_question", "is_answer", "source", "is_active")
    list_filter = ("data_type", "is_question", "is_answer", "source", "is_active")
    search_fields = ("key", "name", "sa_text", "aliases__external_id", "aliases__external_name")
    readonly_fields = ("key", "name", "data_type", "is_question", "is_answer", "source", "created_on")
    fields = ("key", "name", "sa_text", "data_type", "is_question", "is_answer", "source", "is_active", "created_on")
    inlines = [ConceptAliasInline]
    ordering = ("key",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    can_delete = False
    fields = ("question", "group", "repeat_index", "answer", "value_text", "value_number", "value_date", "position")
    readonly_fields = fields
    ordering = ("position", "id")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ("external_id", "kind", "subject_type", "encounter_type", "program", "slum_name",
                    "household_number", "version", "record_datetime", "is_voided", "provider")
    list_filter = ("kind", "provider", "is_voided", "version", "subject_type", "encounter_type", "program")
    search_fields = ("external_id", "subject_external_id", "household_number", "slum_name")
    date_hierarchy = "record_datetime"
    inlines = [AnswerInline]
    ordering = ("-record_datetime", "-id")

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in Record._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SlumDataVersion)
class SlumDataVersionAdmin(admin.ModelAdmin):
    list_display = ("slum", "version", "started_on", "note", "created_by", "created_on")
    list_filter = ("version",)
    search_fields = ("slum__name", "note")
    autocomplete_fields = ("slum",)
    fields = ("slum", "version", "started_on", "note")
    ordering = ("slum__name", "version")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super(SlumDataVersionAdmin, self).save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        return ("slum", "version") if obj else ()

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        return not Record.objects.filter(slum=obj.slum, version=obj.version).exists()

    def get_form(self, request, obj=None, **kwargs):
        form = super(SlumDataVersionAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields["started_on"].help_text = (
            "Records last modified from this moment on belong to the new version; earlier ones stay frozen. "
            "Entered in {}.".format(timezone.get_current_timezone_name())
        )
        return form


@admin.register(SyncSwitch)
class SyncSwitchAdmin(admin.ModelAdmin):
    list_display = ("subject_type", "kind", "program", "encounter_type", "label", "is_enabled", "effective", "is_available", "provider")
    list_editable = ("is_enabled",)
    list_filter = ("provider", "subject_type", "kind", "is_enabled", "is_available")
    search_fields = ("subject_type", "program", "encounter_type", "label")
    readonly_fields = ("provider", "subject_type", "kind", "program", "encounter_type", "label", "form_external_id", "is_available")
    actions = ("enable_selected", "disable_selected")
    ordering = ("subject_type", "kind", "program", "encounter_type")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def effective(self, row):
        """Own flag AND the subject switch; a child of a disabled subject shows greyed."""
        enabled = switches.effective_enabled(row)
        if enabled:
            return format_html('<span style="color:#1a7f37">on</span>')
        if row.is_enabled:
            return format_html('<span style="color:#888" title="its subject type is switched off">off (parent)</span>')
        return format_html('<span style="color:#888">off</span>')
    effective.short_description = "Effective"

    def enable_selected(self, request, queryset):
        count = queryset.update(is_enabled=True)
        self.message_user(request, "{} switch(es) enabled.".format(count), messages.SUCCESS)
    enable_selected.short_description = "Enable selected switches"

    def disable_selected(self, request, queryset):
        count = queryset.update(is_enabled=False)
        self.message_user(request, "{} switch(es) disabled.".format(count), messages.SUCCESS)
    disable_selected.short_description = "Disable selected switches"
