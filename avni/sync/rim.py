"""Slum-level RIM registration and community toilet blocks -> graphs.SlumData.rim_data."""

import json
import logging
from datetime import datetime
from functools import lru_cache

import dateparser

from avni import paths, watermark
from avni.client import client
from avni.locations import data_file, slum_location_uuid
from graphs.models import SlumData
from master.models import Rapid_Slum_Appraisal, Slum
from notification.services import reporting

logger = logging.getLogger(__name__)

RIM_SUBJECT_TYPE = "Slum-RIM Registration"
TOILET_SUBJECT_TYPE = "Toilet"
RIM_SECTIONS = ["General", "Water", "Waste", "Drainage", "Gutter", "Road", "Electricity"]
TOILET_SECTION = "Toilet"

MULTISELECT_QUESTIONS = {
    "Slum Land owner",
    "Development plan reservation type_",
    "Location of slum",
    "Topography of slum",
    "Alternative source of water in slum",
    "Availability of water in slum",
    "Facility of waste collection in slum",
    "Where are the communty open dump sites_",
    "Finish of the road in slum?",
    "Average width of internal roads in slum",
    "Status of defecation",
    "Diameter of ULB sewer line across settlement?",
    "Type of water supply available in CTB",
    "Community Toilet Block maintenance provided by",
    "The reason for men not using the toilet seats",
    "The reason for women not using the toilet seats",
    "The Reason for the MIXED seats not in Use",
}

# AVNI image concept -> Rapid_Slum_Appraisal field
IMAGE_FIELDS = {
    "Toilet Image 1": "toilet_image_bottomdown1",
    "Toilet Image 2": "toilet_image_bottomdown2",
    "Water Image 1": "water_image_bottomdown1",
    "Water Image 2": "water_image_bottomdown2",
    "Waste Image 1": "waste_management_image_bottomdown1",
    "Waste Image 2": "waste_management_image_bottomdown2",
    "Drainage Image 1": "drainage_image_bottomdown1",
    "Drainage Image 2": "drainage_image_bottomdown2",
    "Gutter Image 1": "gutter_image_bottomdown1",
    "Gutter Image 2": "gutter_image_bottomdown2",
    "Road and Access Image 1": "roads_image_bottomdown1",
    "Road and Access Image 2": "road_image_bottomdown2",
    "General Information Image 1": "general_image_bottomdown1",
    "General Information Image 2": "general_image_bottomdown2",
    "Electricity Infrastructure Image 1": "electricity_image_bottomdown1",
    "Electricity Infrastructure Image 2": "electricity_image_bottomdown2",
}


@lru_cache(maxsize=1)
def rim_questions():
    """{section: {shelter key: AVNI concept}} from avni/data/rim_questions_mapping.json."""
    with open(data_file("rim_questions_mapping.json")) as handle:
        return json.load(handle)


def map_section(observations, question_map):
    mapped = {}
    for shelter_key, concept in question_map.items():
        if concept not in observations:
            continue
        value = observations[concept]
        mapped[shelter_key] = ", ".join(value) if concept in MULTISELECT_QUESTIONS else value
    return mapped


def rim_images(observations):
    return {field: observations[concept] for concept, field in IMAGE_FIELDS.items() if concept in observations}


def parse_modified_at(record):
    return datetime.strptime(record["audit"]["Last modified at"], "%Y-%m-%dT%H:%M:%S.%fZ")


def save_rim_record(record, slum_id):
    """Replace the slum's rim_data from one RIM registration; returns True when images were updated too."""
    observations = record["observations"]
    rim_data = {section: map_section(observations, rim_questions()[section]) for section in RIM_SECTIONS}
    rim_data[TOILET_SECTION] = [{"toilet_comment": observations.get("Comment if any ?", "")}]
    modified_at = parse_modified_at(record)

    rows = SlumData.objects.filter(slum_id=slum_id)
    if rows.exists():
        rows.update(rim_data=rim_data, modified_on=modified_at)
    else:
        slum = Slum.objects.get(id=slum_id)
        SlumData.objects.create(
            slum_id=slum_id,
            city_id=slum.electoral_ward.administrative_ward.city.id,
            submission_date=modified_at,
            rim_data=rim_data,
            created_on=dateparser.parse(record["audit"]["Created at"]),
            modified_on=modified_at,
        )
    return save_rim_images(observations, slum_id)


def save_rim_images(observations, slum_id):
    images = rim_images(observations)
    appraisal = Rapid_Slum_Appraisal.objects.filter(slum_name_id=slum_id)
    if images and appraisal.exists():
        appraisal.update(**images)
        return True
    return False


def save_toilet_record(record):
    """Add or replace one community toilet block inside the slum's rim_data['Toilet']."""
    slum_name = record["location"]["Slum"]
    toilet = map_section(record["observations"], rim_questions()[TOILET_SECTION])
    slum_id = Slum.objects.filter(name=slum_name).values_list("id", flat=True).first()
    rows = SlumData.objects.filter(slum_id=slum_id)
    if not rows.exists():
        logger.error("No SlumData for slum %s (%s); toilet %s skipped", slum_name, slum_id, record.get("ID"))
        return False
    rim_data = rows.values_list("rim_data", flat=True)[0] or {}
    toilets = rim_data.get(TOILET_SECTION) or []
    rim_data[TOILET_SECTION] = replace_toilet(toilets, toilet)
    rows.update(rim_data=rim_data)
    return True


def replace_toilet(toilets, toilet):
    name = toilet.get("ctb name")
    for index, existing in enumerate(toilets):
        if existing.get("ctb name") == name:
            toilets[index] = toilet
            return toilets
    toilets.append(toilet)
    return toilets


def sync_slum_rim(slum_id, api=None):
    """(slum is mapped in AVNI, RIM records saved, images updated) for one slum."""
    location_uuid = slum_location_uuid(slum_id)
    if not location_uuid:
        return False, 0, False
    api = api or client()
    saved, images_updated = 0, False
    for page in api.iter_pages(paths.subjects(RIM_SUBJECT_TYPE, watermark.EPOCH, location_uuid)):
        for record in page:
            if record.get("Voided"):
                continue
            with reporting.record(slum=record["location"].get("Slum"), key=record.get("ID")):
                try:
                    images_updated = save_rim_record(record, slum_id) or images_updated
                    saved += 1
                except Exception as exc:
                    logger.error("RIM %s not saved: %s", record.get("ID"), exc)
                    reporting.fail(exc)
    return True, saved, images_updated


def sync_slum_toilets(slum_id, api=None):
    """Number of community toilet blocks saved for one slum."""
    location_uuid = slum_location_uuid(slum_id)
    if not location_uuid:
        return 0
    api = api or client()
    saved = 0
    for page in api.iter_pages(paths.subjects(TOILET_SUBJECT_TYPE, watermark.EPOCH, location_uuid)):
        for record in page:
            if record.get("Voided"):
                continue
            with reporting.record(slum=record["location"].get("Slum"), key=record.get("ID")):
                try:
                    saved += int(save_toilet_record(record))
                except Exception as exc:
                    logger.error("Toilet %s not saved: %s", record.get("ID"), exc)
                    reporting.fail(exc)
    return saved
