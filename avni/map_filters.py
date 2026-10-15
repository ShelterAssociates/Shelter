"""The custom map filters: which forms a slum's preset offers, and the definitions the app evaluates.

The server only authors the definitions. Whether a form is filled for a house is decided on the
phone against its own AVNI data, so the figures are as current as the worker's last sync.
"""

from django.db.models import Q

from avni.models import FILTER_KIND, AvniFilterPresetScope, city_id_of
from helpers.financial_year import current_financial_year, financial_year_label, financial_year_range

FY_BACK = 8
COMPLETENESS_LABEL = "Required forms"


def resolve_preset(slum):
    """The preset for a slum: its own scope row, else its city's, else the global one."""
    rows = (
        AvniFilterPresetScope.objects.filter(preset__is_active=True)
        .filter(
            Q(slum=slum)
            | Q(slum__isnull=True, city_id=city_id_of(slum))
            | Q(slum__isnull=True, city__isnull=True)
        )
        .select_related("preset")
    )
    best = None
    for row in rows:
        # More specific scope wins; between equals, the newest version does.
        rank = (row.slum_id is not None, row.city_id is not None, row.preset.version)
        if best is None or rank > best[0]:
            best = (rank, row.preset)
    return best[1] if best else None


def items_of(preset):
    return (
        preset.items.select_related(
            "mapping", "mapping__form", "anchor_question", "pairs_with", "pairs_with__mapping", "pairs_with__mapping__form",
        )
        .prefetch_related("stages", "stages__question")
        .order_by("order", "id")
    )


def date_presets(back=FY_BACK):
    """Financial years the app offers as ready-made date windows, newest first."""
    current = current_financial_year()
    windows = []
    for year in range(current, current - back, -1):
        start, end = financial_year_range(year)
        windows.append({
            "id": "fy-{}".format(year),
            "label": "FY {}".format(financial_year_label(year)),
            "from": start.isoformat(),
            "to": end.isoformat(),
        })
    return windows


def form_entry(item):
    mapping = item.mapping
    anchor = item.anchor_question
    return {
        "id": item.filter_id,
        "label": item.display_label,
        "kind": FILTER_KIND.get(mapping.form.form_type, "form"),
        "subject_type": mapping.subject_type,
        "program": mapping.program,
        "encounter_type": mapping.encounter_type,
        "form_name": mapping.form.name,
        "required": item.is_required,
        "show_as_filter": item.show_as_filter,
        "rollup": item.rollup,
        "anchor_concept_uuid": anchor.concept_uuid if anchor else None,
        "anchor_concept_name": anchor.concept_name if anchor else "",
        "default_window": item.default_window,
        "colors": {"filled": item.filled_color, "absent": item.absent_color},
    }


def stage_entry(item, stage):
    return {
        "id": "stage:{}".format(stage.id),
        "form_id": item.filter_id,
        "label": stage.label,
        "concept_uuid": stage.question.concept_uuid,
        "concept_name": stage.question.concept_name,
        "kind": stage.kind,
        "color": stage.color,
        "order": stage.order,
    }


def occupancy_entry(preset):
    """The structure-occupancy rule, or None: forms are only expected where the answer says occupied."""
    question = preset.occupancy_question
    answers = [str(answer).strip() for answer in (preset.occupied_answers or []) if str(answer).strip()]
    if question is None or not answers:
        return None
    return {
        "concept_uuid": question.concept_uuid,
        "concept_name": question.concept_name,
        "occupied": answers,
    }


def payload(slum):
    """The custom_filters block for a slum, or None when no preset applies to it."""
    preset = resolve_preset(slum)
    if preset is None:
        return None
    forms, stages, pairs = [], [], []
    for item in items_of(preset):
        forms.append(form_entry(item))
        for stage in item.stages.all():
            stages.append(stage_entry(item, stage))
        if item.pairs_with_id:
            pairs.append({
                "id": "pair:{}".format(item.id),
                "label": item.display_label,
                "pre_form_id": item.filter_id,
                "post_form_id": item.pairs_with.filter_id,
            })
    block = {
        "preset": {"name": preset.name, "version": preset.version},
        "occupancy": occupancy_entry(preset),
        "forms": forms,
        "stages": stages,
        "pairs": pairs,
        "date_presets": date_presets(),
        "filled_by": {"enabled": True},
    }
    if any(form["required"] for form in forms):
        block["completeness"] = {"label": COMPLETENESS_LABEL, "default_window": "overall"}
    return block
