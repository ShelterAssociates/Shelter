from master.models import Slum, Rapid_Slum_Appraisal
from graphs.models import SlumData


# ============================================================
# SECTION ORDER (TOP → BOTTOM)
# ============================================================

RIM_SECTION_ORDER = [
	"General",
	"Toilet",
	"Water",
	"Road",
	"Drainage",
	"Gutter",
	"Waste",
]


# ============================================================
# ADDITIONAL INFO FIELDS (MODEL)
# ============================================================

RIM_ADDITIONAL_INFO_SECTION_FIELDS = {
	"General": [
		"approximate_population",
		"general_info_left_image",
		"general_image_bottomdown1",
		"general_image_bottomdown2",
	],
	"Toilet": [
		"toilet_cost",
		"toilet_seat_to_persons_ratio",
		"percentage_with_individual_toilet",
		"toilet_info_left_image",
		"toilet_image_bottomdown1",
		"toilet_image_bottomdown2",
	],
	"Water": [
		"percentage_with_an_individual_water_connection",
		"water_info_left_image",
		"water_image_bottomdown1",
		"water_image_bottomdown2",
	],
	"Road": [
		"roads_and_access_info_left_image",
		"roads_image_bottomdown1",
		"road_image_bottomdown2",
	],
	"Drainage": [
		"drainage_coverage",
		"drainage_info_left_image",
		"drainage_image_bottomdown1",
		"drainage_image_bottomdown2",
	],
	"Gutter": [
		"gutter_info_left_image",
		"gutter_image_bottomdown1",
		"gutter_image_bottomdown2",
	],
	"Waste": [
		"frequency_of_clearance_of_waste_containers",
		"waste_management_info_left_image",
		"waste_management_image_bottomdown1",
		"waste_management_image_bottomdown2",
	],
}


# ============================================================
# RIM FORM → DISPLAY LABEL MAPPING
# ============================================================

RIM_MAP_KEYS = {
	"General": {
		"slum_name": "Name of Slum",
		"survey_sector_number": "Survey / Sector Number",
		"admin_ward": "Administrative Ward",
		"approximate_area_of_the_settle": "Approximate Area of Settlement",
		"number_of_huts_in_settlement": "Number of Huts in Settlement",
		"year_established_according_to": "Year Established",
		"legal_status": "Legal Status of Slum",
		"land_owner": "Land Ownership",
		"topography": "Topography",
		"landmark": "Nearby Landmark",
		"Number_of_Anganwadis_in_the_slum": "Number of Anganwadis in the Slum",
		"Name_of_NGOs_working_in_the_slum": "NGOs Working in the Slum",
		"describe_the_slum": "Description of the Slum",
		"development_plan_reservation": "Development Plan Reservation",
		"development_plan_reservation_t": "Development Plan Reservation Type",
		"Date_of_declaration": "Date of Declaration",
		"location": "Location",
	},
	"Drainage": {
		"presence_of_drains_within_the": "Presence of Drains",
		"coverage_of_drains_across_the": "Coverage of Drains",
		"do_the_drains_get_blocked": "Do Drains Get Blocked?",
		"is_the_drainage_gradient_adequ": "Drainage Gradient Adequate?",
		"diameter_of_ulb_sewer_line_acr": "Diameter of ULB Sewer Line",
		"drainage_comment": "Drainage Remarks",
		"Drainage_Photo1": "Drainage Photo 1",
		"Drainage_Photo2": "Drainage Photo 2",
	},
	"Gutter": {
		"Presence_of_gutter": "Presence of Gutter",
		"coverage_of_gutter": "Coverage of Gutter",
		"do_gutter_get_choked": "Do Gutters Get Choked?",
		"do_gutters_flood": "Do Gutters Flood?",
		"is_gutter_gradient_adequate": "Gutter Gradient Adequate?",
		"type_of_gutter_within_the_sett": "Type of Gutter",
		"comments_on_gutter": "Gutter Remarks",
		"Gutter_Photo1": "Gutter Photo",
	},
	"Road": {
		"presence_of_roads_within_the_s": "Presence of Roads",
		"type_of_roads_within_the_settl": "Type of Roads",
		"average_width_of_arterial_road": "Average Width of Arterial Road",
		"average_width_of_internal_road": "Average Width of Internal Roads",
		"finish_of_the_road": "Road Finish",
		"point_of_vehicular_access_to_t": "Point of Vehicular Access",
		"road_and_access_comment": "Road & Access Remarks",
		"Road_Photo1": "Road Photo 1",
		"Road_Photo2": "Road Photo 2",
	},
	"Water": {
		"availability_of_water": "Availability of Water",
		"quality_of_water_in_the_system": "Quality of Water",
		"pressure_of_water_in_the_syste": "Water Pressure",
		"total_number_of_handpumps_in_u": "Total Number of Handpumps",
		"Total_number_of_standposts_in_": "Total Number of Standposts",
		"total_number_of_taps_in_use_n": "Total Number of Taps in Use",
		"alternative_source_of_water": "Alternative Source of Water",
		"water_supply_comment": "Water Supply Remarks",
		"Water_Photo1": "Water Photo 1",
		"Water_Photo2": "Water Photo 2",
	},
	"Waste": {
		"coverage_of_waste_collection_a": "Coverage of Waste Collection",
		"facility_of_waste_collection": "Facility of Waste Collection",
		"frequency_of_waste_collection": "Frequency of Waste Collection",
		"total_number_of_waste_containe": "Total Number of Waste Containers",
		"Is wet and dry garbage collected seperately ?": "Wet & Dry Waste Collected Separately?",
		"do_the_member_of_community_dep": "Community Dependent on Waste Facility",
		"where_are_the_communty_open_du": "Location of Community Open Dumping",
		"Waste_management_comments": "Waste Management Remarks",
		"Waste_Management_Photo1": "Waste Management Photo 1",
		"Waste_Management_Photo2": "Waste Management Photo 2",
	},
}


# ============================================================
# FIELD ORDER (FORM + ADDITIONAL COMBINED)
# ============================================================

RIM_SECTION_FIELD_ORDER = {
	"General": list(RIM_MAP_KEYS["General"].values()) +
		RIM_ADDITIONAL_INFO_SECTION_FIELDS["General"],

	"Drainage": list(RIM_MAP_KEYS["Drainage"].values()) +
		RIM_ADDITIONAL_INFO_SECTION_FIELDS["Drainage"],

	"Gutter": list(RIM_MAP_KEYS["Gutter"].values()) +
		RIM_ADDITIONAL_INFO_SECTION_FIELDS["Gutter"],

	"Road": list(RIM_MAP_KEYS["Road"].values()) +
		RIM_ADDITIONAL_INFO_SECTION_FIELDS["Road"],

	"Water": list(RIM_MAP_KEYS["Water"].values()) +
		RIM_ADDITIONAL_INFO_SECTION_FIELDS["Water"],

	"Waste": list(RIM_MAP_KEYS["Waste"].values()) +
		RIM_ADDITIONAL_INFO_SECTION_FIELDS["Waste"],
}


# ============================================================
# HELPERS
# ============================================================

def serialize_field(obj, field):
	value = getattr(obj, field)
	if hasattr(value, "url"):
		return value.url if value else None
	return value


def map_rim_form_data(rim_form_data):
	mapped = {}
	for section, key_map in RIM_MAP_KEYS.items():
		source = rim_form_data.get(section)
		if not isinstance(source, dict):
			continue

		mapped[section] = {
			dest: source[src]
			for src, dest in key_map.items()
			if src in source
		}
	return mapped


def build_rim_additional_info_sections(obj):
	data = {}
	for section, fields in RIM_ADDITIONAL_INFO_SECTION_FIELDS.items():
		data[section] = {
			field: serialize_field(obj, field)
			for field in fields
			if serialize_field(obj, field) is not None
		}
	return data


def merge_and_order_sections(form_data, additional_data):
	sections = {}

	for section in RIM_SECTION_ORDER:
		merged = {}
		merged.update(form_data.get(section, {}))
		merged.update(additional_data.get(section, {}))

		if not merged:
			continue

		ordered = []
		for idx, key in enumerate(RIM_SECTION_FIELD_ORDER.get(section, []), start=1):
			if key in merged:
				ordered.append({
					"label": key,
					"order": idx,
					"value": merged[key]
				})

		sections[section] = ordered

	return sections


# ============================================================
# MAIN SERVICE
# ============================================================

def get_rim_factsheet_data(slum_id):
	try:
		slum = Slum.objects.get(id=slum_id)

		rim_form = SlumData.objects.filter(slum=slum).first()
		rim_additional = Rapid_Slum_Appraisal.objects.filter(slum_name=slum).first()

		form_data = map_rim_form_data(rim_form.rim_data) if rim_form else {}
		additional_data = build_rim_additional_info_sections(rim_additional) if rim_additional else {}

		sections = merge_and_order_sections(form_data, additional_data)

		return {
			"slum_id": slum.id,
			"slum_name": slum.name,
			"sections": sections
		}

	except Slum.DoesNotExist:
		return {"error": "Slum not found"}

	except Exception as e:
		return {"error": str(e)}
