import requests
from collections import OrderedDict, Counter
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import json
from master.models import Slum
from graphs.models import SlumData
from graphs.sync_avni_data import avni_sync


AVNI_SIGNED_URL_API = "https://app.avniproject.org/media/signedUrl?url="
SHELTER_MEDIA_PREFIX = "https://app.shelter-associates.org/media/"

#=====================================================
# Mapping of RIM Factsheet fields to display names
#=====================================================

RIM_FIELD_DISPLAY_NAMES = {
  "meta_data": {
      "submission_date": "submission_date",
      "modified_on": "last_modified_on",
	  "city_name": "city_name",
	  "admin_ward": "admin_ward",
	  "electoral_ward": "electoral_ward",
	  "slum_name": "slum_name",
	  "_exists" : "_exists"
  },
  "sections": {
    "General": {
      "general_info_left_image": "general_info_map",
      "year_established_according_to": "Year Established",
      "legal_status": "Legal Status of Slum",
      "Date_of_declaration": "Date of Declaration",
      "land_owner": "Land Ownership",
      "development_plan_reservation": "Development Plan Reservation",
      "approximate_area_of_the_settle": "Approximate Area of Settlement",
      "number_of_huts_in_settlement": "Number of Huts in Settlement",
      "approximate_population": "Approximate Population",
      "location": "Location",
      "topography": "Topography",
      "landmark": "Nearby Landmark",
      "describe_the_slum": "Description of the Slum_observations",
      "general_image_bottomdown1": "general_image_1_bottom1",
      "general_image_bottomdown2": "general_image_2_bottom2"
    },

    "Toilet": {
	  "toilet_info_left_image": "toilet_info_map",
      "number_of_community_toilet_blo": "Number of Community Toilet Blocks",
      "number_of_seats_allotted_to_wo": "Seats for Women",
      "number_of_seats_allotted_to_me": "Seats for Men",
      "total_number_of_mixed_seats_al": "Mixed Seats",
      "ctb_maintenance_provided_by": "CTB Maintenance Provided By",
      "condition_of_ctb_structure": "Condition of Toilet Structure",
      "cleanliness_of_the_ctb": "Cleanliness of Toilet Block",
      "type_of_water_supply_in_ctb": "Water Supply in Toilet Block",
      "facility_in_the_toilet_block_f": "Facilities in Toilet Block",
      "sewage_disposal_system": "Sewage Disposal System",
      "toilet_comment": "Toilet Observations",
      "percentage_with_individual_toilet": "Households with Individual Toilets (%)",
      "toilet_cost": "Cost of Toilet",
      "toilet_seat_to_persons_ratio": "Toilet Seat to Person Ratio",
      "location_of_defecation": "Location of Open Defecation",
	  "toilet_comment" : "Toilet Observations_observations",
      "toilet_image_bottomdown1": "toilet_image_1_bottom1",
      "toilet_image_bottomdown2": "toilet_image_2_bottom2"
    },

    "Water": {
	  "water_info_left_image": "general_water_supply_map",
      "Total_number_of_standposts_in_": "Total Number of Standposts",
      "Total_number_of_standposts_NOT": "Non-Functional Standposts",
      "total_number_of_taps_in_use_n": "Total Number of Taps in Use",
      "total_number_of_handpumps_in_u": "Total Number of Handpumps",
      "alternative_source_of_water": "Alternative Source of Water",
      "availability_of_water": "Availability of Water",
      "pressure_of_water_in_the_syste": "Water Pressure",
      "coverage_of_wateracross_settle": "Coverage of Water Across Settlement",
      "quality_of_water_in_the_system": "Quality of Water",
      "percentage_with_an_individual_water_connection": "Households with Individual Water Connection (%)",
	  "water_supply_comment": "Water Supply Observations_observations",
      
      "water_image_bottomdown1": "water_image_bottom1",
      "water_image_bottomdown2": "water_image_bottom2",
      "Water_Photo1": "Water Photo 1",
      "Water_Photo2": "Water Photo 2"
    },

    "Road": {
	  "roads_and_access_info_left_image": "roads_and_access_map",
      "presence_of_roads_within_the_s": "Presence of Roads",
      "type_of_roads_within_the_settl": "Type of Roads",
      "coverage_of_pucca_road_across": "Pucca Road Coverage (%)",
      "finish_of_the_road": "Road Surface Finish",
      "average_width_of_internal_road": "Average Width of Internal Roads",
      "average_width_of_arterial_road": "Average Width of Arterial Road",
      "point_of_vehicular_access_to_t": "Point of Vehicular Access",
      "is_the_settlement_below_or_abo": "Settlement Level (Above/Below Road)",
      "are_the_huts_below_or_above_th": "Hut Level (Above/Below Road)",
      "road_and_access_comment": "Road & Access Observations_observations",
      "roads_image_bottomdown1": "roads_image_bottom1",
      "road_image_bottomdown2": "road_image_bottom2",
      "Road_Photo1": "Road Photo 1",
      "Road_Photo2": "Road Photo 2"
    },

    "Drainage": {
	  "drainage_info_left_image": "drainage_info_map",
      "presence_of_drains_within_the": "Presence of Drains",
      "coverage_of_drains_across_the": "Coverage of Drains",
      "do_the_drains_get_blocked": "Do Drains Get Blocked?",
      "is_the_drainage_gradient_adequ": "Drainage Gradient Adequate?",
      "diameter_of_ulb_sewer_line_acr": "Diameter of ULB Sewer Line",

      "drainage_coverage": "Overall Drainage Coverage",
      "drainage_comment": "Drainage Observations_observations",
      "drainage_image_bottomdown1": "drainage_image_bottom1",
      "drainage_image_bottomdown2": "drainage_image_bottom2",
      "Drainage_Photo1": "Drainage_bottom1",
      "Drainage_Photo2": "Drainage_bottom2"
    },

    "Gutter": {
	  "gutter_info_left_image": "general_gutter_map",
      "Presence_of_gutter": "Presence of Gutter",
      "type_of_gutter_within_the_sett": "Type of Gutter",
      "coverage_of_gutter": "Coverage of Gutter",
      "are_gutter_covered": "Are Gutters Covered?",
      "do_gutters_flood": "Do Gutters Flood?",
      "do_gutter_get_choked": "Do Gutters Get Choked?",
      "is_gutter_gradient_adequate": "Gutter Gradient Adequate?",
      "comments_on_gutter": "Gutter Observations_observations",
      "gutter_image_bottomdown1": "gutter_image_bottom1",
      "gutter_image_bottomdown2": "gutter_image_bottom2",
      "Gutter_Photo1": "Gutter Photo"
    },

    "Waste": {
	  "waste_management_info_left_image": "Waste Management Map", 
      "total_number_of_waste_containe": "Total Number of Waste Containers",
      "facility_of_waste_collection": "Facility of Waste Collection",
      "frequency_of_waste_collection": "Frequency of Waste Collection",
      "coverage_of_waste_collection_a": "Coverage of Waste Collection",
      "where_are_the_communty_open_du": "Location of Community Open Dumping",
      "do_the_member_of_community_dep": "Community Dependent on Waste Facility",
      "Is wet and dry garbage collected seperately ?": "Wet & Dry Waste Collected Separately?",
      
      "frequency_of_clearance_of_waste_containers": "Waste Container Clearance Frequency",
	"Waste_management_comments": "Waste Management Observations_observations",
 
      "waste_management_image_bottomdown1": "waste_image_bottom1",
      "waste_management_image_bottomdown2": "waste_image_bottom2",
      "Waste_Management_Photo1": "Waste_Management_bottom1",
      "Waste_Management_Photo2": "Waste_Management_bottom2"
    }
  }
}

#=====================================================
# Map Rim Factsheet fields to display names
#=====================================================
def map_rim_data(raw_data: dict) -> dict:
	"""
	Map raw RIM JSON to display-labeled, section-wise structure.
	"""
	result = OrderedDict()

	# ---------------- META DATA ----------------
	meta_output = OrderedDict()
	meta_fields = RIM_FIELD_DISPLAY_NAMES.get("meta_data", {})

	for field_key, display_name in meta_fields.items():
		if field_key in raw_data:
			meta_output[display_name] = raw_data[field_key]

	result["meta_data"] = meta_output

	# ---------------- SECTIONS ----------------
	sections_output = OrderedDict()
	section_definitions = RIM_FIELD_DISPLAY_NAMES.get("sections", {})

	for section_name, fields in section_definitions.items():
		section_data = OrderedDict()

		for field_key, display_name in fields.items():
			if field_key in raw_data:
				value = raw_data.get(field_key)
				if value in ("", None, [], {}):
					continue
				section_data[display_name] = value

		if section_data:
			sections_output[section_name] = section_data

	result["sections"] = sections_output

	print("RIM Factsheet Mapped Data:")
	print(json.dumps(result, indent=2))

	return result


# ======================================================
# AVNI TOKEN (CACHED FOR PERFORMANCE)
# ======================================================
@lru_cache(maxsize=1)
def get_avni_token():
	return avni_sync().get_cognito_token()


# ======================================================
# CORE RIM FACTSHEET DATA
# ======================================================
def get_rim_factsheet_detail(slum_code):
	"""
	Prepare RIM factsheet core data for a given slum code.
	"""
	result = OrderedDict()

	# ---- Fetch slum
	slum = (
		Slum.objects
		.only("id", "shelter_slum_code")
		.filter(shelter_slum_code=slum_code)
		.first()
	)
	if not slum:
		return result

	# ---- Fetch slum data
	slum_data = (
		SlumData.objects
		.only("rim_data", "submission_date", "modified_on")
		.filter(slum_id=slum.id)
		.first()
	)
	if not slum_data or not slum_data.rim_data:
		return result

	data = slum_data.rim_data
	get = data.get
	update = result.update

	# ---- Dates
	result["submission_date"] = (
		slum_data.submission_date.strftime("%B %Y")
		if slum_data.submission_date else "NA"
	)
	result["modified_on"] = (
		slum_data.modified_on.strftime("%B %Y")
		if slum_data.modified_on else "NA"
	)

	# ---- Merge section helper
	def merge_section(section):
		section_data = get(section)
		if isinstance(section_data, dict):
			update(section_data)

	# ---- Merge base sections
	for section in ("General", "Waste", "Water", "Drainage", "Road", "Gutter"):
		merge_section(section)

	# ==================================================
	# TOILET SECTION (FULL LOGIC)
	# ==================================================
	def counter_to_string(counter):
		return ", ".join("{}({})".format(k, v) for k, v in counter.items())

	toilet_entries = get("Toilet", [])

	if toilet_entries:
		result["number_of_community_toilet_blo"] = 0
		result["toilet_comment"] = toilet_entries[0].get("toilet_comment", "")

		seats = {"women": 1, "men": 1, "mixed": 1}
		ctb_stats = {
			"ctb_maintenance_provided_by": Counter(),
			"condition_of_ctb_structure": Counter(),
			"cleanliness_of_the_ctb": Counter(),
			"facility_in_the_toilet_block_f": Counter(),
			"sewage_disposal_system": Counter(),
			"type_of_water_supply_in_ctb": Counter(),
		}

		for entry in toilet_entries:
			if "ctb name" in entry:
				result["number_of_community_toilet_blo"] += 1

			if entry.get("is_the_CTB_in_use") != "Yes":
				continue

			seats["women"] += int(entry.get("number_of_seats_allotted_to_wo", 0))
			seats["men"] += int(entry.get("number_of_seats_allotted_to_me", 0))
			seats["mixed"] += int(entry.get("total_number_of_mixed_seats_al", 0))

			for key in (
				"ctb_maintenance_provided_by",
				"condition_of_ctb_structure",
				"cleanliness_of_the_ctb",
				"facility_in_the_toilet_block_f",
				"sewage_disposal_system",
			):
				val = entry.get(key)
				if val:
					ctb_stats[key][val] += 1

			for supply in entry.get("type_of_water_supply_in_ctb", "").split(","):
				if supply:
					ctb_stats["type_of_water_supply_in_ctb"][supply.strip()] += 1

		update({
			"number_of_seats_allotted_to_wo": seats["women"],
			"number_of_seats_allotted_to_me": seats["men"],
			"total_number_of_mixed_seats_al": seats["mixed"],
		})

		for key, counter in ctb_stats.items():
			result[key] = counter_to_string(counter)

	else:
		update({
			"number_of_community_toilet_blo": 1,
			"number_of_seats_allotted_to_wo": 1,
			"number_of_seats_allotted_to_me": 1,
			"total_number_of_mixed_seats_al": 1,
		})
	# print(json.dumps(result, indent=2))
	return result


# ======================================================
# IMAGE URL RESOLUTION
# ======================================================
def _fetch_signed_url(field_name, raw_url, token):
	try:
		resp = requests.get(
			AVNI_SIGNED_URL_API + raw_url,
			headers={"AUTH-TOKEN": token},
			timeout=10
		)
		return field_name, resp.text
	except Exception:
		return field_name, raw_url


def resolve_rim_images(rim_record):
	"""
	Resolve AVNI and Shelter image URLs in RIM image record.
	"""
	image_fields = [
		"toilet_image_bottomdown1", "toilet_image_bottomdown2",
		"water_image_bottomdown1", "water_image_bottomdown2",
		"waste_management_image_bottomdown1", "waste_management_image_bottomdown2",
		"drainage_image_bottomdown1", "drainage_image_bottomdown2",
		"gutter_image_bottomdown1", "gutter_image_bottomdown2",
		"roads_image_bottomdown1", "road_image_bottomdown2",
		"general_image_bottomdown1", "general_image_bottomdown2",
		"general_info_left_image", "toilet_info_left_image",
		"waste_management_info_left_image", "water_info_left_image",
		"roads_and_access_info_left_image", "drainage_info_left_image",
		"gutter_info_left_image", "drainage_report_image",
	]

	avni_images = {}

	for field in image_fields:
		value = str(rim_record.get(field, ""))

		if value.startswith("https://s3.ap-south-1.amazonaws.com/"):
			avni_images[field] = value
		elif "ShelterPhotos" in value:
			rim_record[field] = SHELTER_MEDIA_PREFIX + value

	if not avni_images:
		return rim_record

	token = get_avni_token()

	with ThreadPoolExecutor(max_workers=6) as executor:
		for key, url in executor.map(
			lambda item: _fetch_signed_url(item[0], item[1], token),
			avni_images.items()
		):
			rim_record[key] = url

	return rim_record
