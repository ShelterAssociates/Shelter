import base64
import logging
import json
import re
import requests
import subprocess
import threading
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple
from urllib.parse import quote

from django.conf import settings
from django.db import close_old_connections

from graphs.sync_avni_data import avni_sync  # adjust to the actual module name
from mastersheet.models import HouseholdData

logger = logging.getLogger(__name__)

# Master question -> rhs_data key map, consolidated from the legacy
# map_rhs_key / map_sanitation_keys dicts plus the Structure/DSES field
# mappings worked out earlier. Any incoming key NOT listed here is written
# through unchanged (new questions get added as new fields, as requested).
KNOWN_QUESTION_MAP = {
    # identity / core registration
    "uuid": "rhs_uuid",
    "first_name": "Household_number",
    "First name": "Household_number",
    "Househhold number": "Enter_household_number_again",
    "Ward No": "Select Ward",
    "Date of Survey": "Date_of_survey",
    "Additional Comment": "Comment ?",
    "Comment": "Comment ?",
    "Surveyor (normal/coded)": "Name_s_of_the_surveyor_s",
    "Name of the surveyor": "Name_s_of_the_surveyor_s",
    "Updated by (normal/coded)": "Name of surveyor who updated the data",

    # structure / occupancy
    "Type of structure occupancy_1": "Type_of_structure_occupancy",
    "Type of structure occupancy": "Type_of_structure_occupancy",
    "Type of structure of the house_1": "group_el9cl08/Type_of_structure_of_the_house",
    "Type of structure of the house": "group_el9cl08/Type_of_structure_of_the_house",
    "Ownership status of the house_1": "group_el9cl08/Ownership_status_of_the_house",
    "Ownership status of the house": "group_el9cl08/Ownership_status_of_the_house",
    "Type of unoccupied house_1": "Type_of_unoccupied_house",
    "Type of unoccupied house": "Type_of_unoccupied_house",
    "Number of flats in the building ?": "Number of units in the building ?",
    "Parent household number": "Parent_household_number",
    "House area in square feets.": "group_el9cl08/House_area_in_sq_ft",

    # household / members
    "Full name of the head of the household": "group_og5bx85/Full_name_of_the_head_of_the_household",
    "Enter the 10 digit mobile number": "group_el9cl08/Enter_the_10_digit_mobile_number",
    "Contact number of respondent": "group_el9cl08/Enter_the_10_digit_mobile_number",
    "Number of household members": "group_el9cl08/Number_of_household_members",
    "total_members": "group_el9cl08/Number_of_household_members",
    "total_male_members": "Total number of male members (including children)",
    "total_female_members": "Total number of female members (including children)",
    "total_third_gender_members": "Total number of third gender members (including children)?",
    "Aadhaar number": "group_el9cl08/Aadhar_number",
    "Aadhaar Number of the beneficiary": "group_el9cl08/Aadhar_number",
    "Do you have any girl child/children under the age of 18?_": "group_el9cl08/Do_you_have_any_girl_child_chi",

    # water
    "Type of water connection ?": "group_el9cl08/Type_of_water_connection",
    "Water Sub Category": "group_el9cl08/Type_of_water_connection",

    # waste
    "How do you dispose your solid waste ?": "group_el9cl08/Facility_of_solid_waste_collection",
    "How do you dispose your solid waste": "group_el9cl08/Facility_of_solid_waste_collection",

    # sanitation / toilet
    "Current place of defecation": "group_oi8ts04/Current_place_of_defecation",
    "Final current place of defecation": "group_oi8ts04/Current_place_of_defecation",
    "Have you applied for an individual toilet under SBM?_1": "group_oi8ts04/Have_you_applied_for_individua",
    "Status of toilet under SBM ?": "group_oi8ts04/Status_of_toilet_under_SBM",
    "Where the individual toilet is connected to ?": "group_oi8ts04/What_is_the_toilet_connected_to",
    "Who all use toilets in the household ?": "group_oi8ts04/Who_all_use_toilets_in_the_hou",
    "What was the cost incurred to build the toilet?": "group_oi8ts04/What_was_the_cost_in_to_build_the_toilet",
    "Type of SBM toilets ?": "group_oi8ts04/Type_of_SBM_toilets",
    "Reason for not using toilet ?": "group_oi8ts04/Reason_for_not_using_toilet",
    "How many installments have you received ?": "group_oi8ts04/How_many_installments_have_you",
    "When did you receive your first SBM installment?": "group_oi8ts04/When_did_you_receive_ur_first_installment",
    "When did you receive your second SBM installment?": "group_oi8ts04/When_did_you_receive_r_second_installment",
    "When did you receive your third SBM installment?": "group_oi8ts04/When_did_you_receive_ur_third_installment",
    "If built by contractor, how satisfied are you?": "group_oi8ts04/If_built_by_contract_ow_satisfied_are_you",
    "Does any member of the household go for open defecation ?": "group_oi8ts04/OD1",
    "Is there availability of drainage to connect it to the toilet?": "group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets",
    "Is drainage line available ?": "group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets",
    "Are you interested in an individual toilet ?": "group_oi8ts04/Are_you_interested_in_an_indiv",
    "What kind of toilet would you like ?": "group_oi8ts04/What_kind_of_toilet_would_you_like",
    "Under what scheme would you like your toilet to be built ?": "group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built",
    "If yes for individual toilet , why?": "group_oi8ts04/If_yes_why",
    "If no for individual toilet , why?": "group_oi8ts04/If_no_why",
    "Which CTB do your family members use ?": "group_oi8ts04/Which_Community_Toil_r_family_members_use",
    "Does any household member have any of the construction skills given below ?": "group_el9cl08/Does_any_household_m_n_skills_given_below",
    "Does any household member have any of the construction skills ?": "group_el9cl08/Does_any_household_m_n_skills_given_below",
}

# Structural / lookup columns -- never written into the rhs_data JSON blob.
METADATA_KEYS = {
    "Slum", "Slum id", "id", "created_by_user", "last_modified_by_user",
    "created_date_time", "last_modified_date_time", "registration_date",
    "registration_location", "Subject ID", "Voided",
}

# The 5 direct encounters to keep in sync alongside subject registration.
ENCOUNTER_TYPES = ["Sanitation", "Property tax", "Water", "Waste", "Electricity"]

# (condition_key, condition_value, target_key, target_value)
CONDITIONAL_OVERRIDES = (
    ("Do you have a toilet at home?", "Yes", "group_oi8ts04/Current_place_of_defecation", "Own toilet"),
    ("group_el9cl08/Ownership_status_of_the_house", "Own house/Shop", "group_el9cl08/Ownership_status_of_the_house", "Own house"),
)


class AvniHouseholdSync(avni_sync):
    """Reusable sync engine for any Avni subject type or direct encounter type.

    One save pipeline (save_subject_record) handles Structure, Detailed Socio
    Economic Survey, or any future subject type -- just pass a different
    subject_type string to sync_subject(). One merge pipeline
    (save_encounter_record) handles all 5 direct encounters via sync_encounter()
    / sync_all_encounters(). Only cognito auth and get_city_slum_ids are
    inherited from avni_sync; everything else here is self-contained.
    """

    DEFAULT_LAST_MODIFIED = "2000-10-31T01:30:00.000Z"

    # Class-level so the cached token is shared across every AvniHouseholdSync
    # instance/thread in this process, instead of each one shelling out to
    # token.js on every single API call.
    _token_cache = {"token": None, "expires_at": 0}
    _token_lock = threading.Lock()
    TOKEN_REFRESH_MARGIN_SECONDS = 60

    COGNITO_DETAILS_TIMEOUT_SECONDS = 30
    TOKEN_SUBPROCESS_TIMEOUT_SECONDS = 60

    def get_cognito_token(self):
        """Overrides avni_sync.get_cognito_token: reuses a cached JWT until it's
        close to expiry, and -- unlike the inherited version -- puts a hard
        timeout on both the cognito-details HTTP call and the node subprocess so
        a slow/unresponsive Avni can't hang the whole sync forever (that's what
        was freezing the run: no timeout meant one stuck thread held the shared
        lock indefinitely, blocking every other worker behind it)."""
        with AvniHouseholdSync._token_lock:
            cached = AvniHouseholdSync._token_cache
            if cached["token"] and time.time() < cached["expires_at"] - self.TOKEN_REFRESH_MARGIN_SECONDS:
                self.token = cached["token"]
                return self.token

            cognito_details = requests.get(
                self.base_url + "cognito-details", timeout=self.COGNITO_DETAILS_TIMEOUT_SECONDS
            )
            cognito_details = json.loads(cognito_details.text)
            self.poolId = cognito_details["poolId"]
            self.clientId = cognito_details["clientId"]

            result = subprocess.run(
                ["node", "graphs/avni/token.js", self.poolId, self.clientId, settings.AVNI_USERNAME, settings.AVNI_PASSWORD],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=self.TOKEN_SUBPROCESS_TIMEOUT_SECONDS,
            )
            decoded = result.stdout.decode("utf-8")
            lines = [line.strip() for line in decoded.splitlines() if line.strip()]
            token = lines[-1]
            self.token = token

            expires_at = self._jwt_expiry(token) or (time.time() + 3300)
            AvniHouseholdSync._token_cache = {"token": token, "expires_at": expires_at}
            return token

    @staticmethod
    def _jwt_expiry(token: str) -> Optional[float]:
        """Reads the `exp` claim straight out of the JWT payload -- no external lib needed."""
        try:
            payload_b64 = token.split(".")[1]
            padded = payload_b64 + "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))
            return payload.get("exp")
        except Exception:
            return None

    # Avni started returning 403s under sustained/parallel load -- pause briefly
    # every N requests (shared across threads) to back off before that happens.
    # _pause_until is a shared deadline: every thread checks it before firing a
    # request, so hitting the batch size actually stops ALL workers, not just
    # the one thread that happened to make the Nth request (sleeping only that
    # one thread was the earlier bug -- the other workers kept firing the whole time).
    _request_count = 0
    _request_count_lock = threading.Lock()
    _pause_until = 0.0
    REQUEST_BATCH_SIZE = 100
    REQUEST_BATCH_SLEEP_SECONDS = 15

    REQUEST_TIMEOUT_SECONDS = 30

    def _wait_for_batch_pause(self):
        while True:
            remaining = AvniHouseholdSync._pause_until - time.time()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 1))

    def _throttled_get(self, url: str, headers: dict) -> requests.Response:
        self._wait_for_batch_pause()
        response = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT_SECONDS)
        with AvniHouseholdSync._request_count_lock:
            AvniHouseholdSync._request_count += 1
            count = AvniHouseholdSync._request_count
            if count % self.REQUEST_BATCH_SIZE == 0:
                AvniHouseholdSync._pause_until = time.time() + self.REQUEST_BATCH_SLEEP_SECONDS
                print(f"-- {count} requests made, pausing ALL workers for {self.REQUEST_BATCH_SLEEP_SECONDS}s --")
        return response

    def build_url(self, endpoint: str, type_param: str, type_value: str, last_modified_date_time: str = None, location_id: str = None, concepts=None, version: int = 1, page: int = None) -> str:
        last_modified_date_time = last_modified_date_time or self.DEFAULT_LAST_MODIFIED
        params = [("lastModifiedDateTime", last_modified_date_time), (type_param, type_value)]
        params += [("locationIds", location_id)] if location_id else []
        params += [("version", version)] if version is not None else []
        params += [("page", page)] if page is not None else []
        query_string = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params)
        concepts_json = concepts if isinstance(concepts, str) else json.dumps(concepts) if concepts else None
        query_string += f"&concepts={quote(concepts_json, safe='')}" if concepts_json else ""
        return f"{endpoint}?{query_string}"

    def fetch_page(self, endpoint: str, type_param: str, type_value: str, last_modified_date_time: str = None, location_id: str = None, concepts=None, version: int = 1, page: int = 0) -> Optional[dict]:
        url_path = self.build_url(endpoint, type_param, type_value, last_modified_date_time, location_id, concepts, version, page)
        response = self._throttled_get(self.base_url + url_path, headers={"accept": "application/json", "AUTH-TOKEN": self.get_cognito_token()})
        if response.status_code != 200:
            logger.error("%s request failed with status %s (page %s)", type_value, response.status_code, page)
            return None
        return json.loads(response.text)

    @staticmethod
    def map_fields(observations: dict) -> dict:
        return {KNOWN_QUESTION_MAP.get(key, key): value for key, value in observations.items() if key not in METADATA_KEYS}

    @staticmethod
    def apply_conditional_overrides(rhs_data: dict) -> dict:
        for condition_key, condition_value, target_key, target_value in CONDITIONAL_OVERRIDES:
            if rhs_data.get(condition_key) == condition_value:
                rhs_data[target_key] = target_value
        return rhs_data

    HOUSEHOLD_NUMBER_LEADING_ZEROS_RE = re.compile(r"^0*(\d+)([A-Za-z].*)$")

    @classmethod
    def derive_household_number(cls, value) -> str:
        value = str(value or "").strip()
        if value.isdigit():
            return str(int(value))
        # Alphanumeric (e.g. "0022A") -- strip leading zeros off the numeric
        # prefix only, same as the pure-digit case above, so "22A" and "0022A"
        # normalize to the same lookup key instead of being treated as two
        # different households.
        match = cls.HOUSEHOLD_NUMBER_LEADING_ZEROS_RE.match(value)
        return match.group(1) + match.group(2) if match else value

    def save_subject_record(self, record: dict) -> bool:
        observations = record.get("observations") or {}
        if not observations:
            return False

        rhs_data = self.map_fields(observations)
        rhs_data = self.apply_conditional_overrides(rhs_data)
        rhs_data.setdefault("group_og5bx85/Type_of_survey", "RHS")
        rhs_data.setdefault("rhs_uuid", record.get("ID") or record.get("uuid"))

        household_number = self.derive_household_number(
                observations.get("First name")
            )
        rhs_data["Household_number"] = household_number
        slum_name = (record.get("location") or {}).get("Slum") or record.get("Slum")
        if not slum_name:
            logger.error("Missing slum name for record %s", rhs_data.get("rhs_uuid"))
            return False

        try:
            slum_id, city_id = self.get_city_slum_ids(slum_name)
        except Exception as e:
            logger.error("Slum lookup failed for '%s': %s", slum_name, e)
            return False

        created_date = record.get("registration_date") or record.get("Registration date")
        submission_date = record.get("last_modified_date_time") or (record.get("audit") or {}).get("Last modified at")

        existing = HouseholdData.objects.filter(household_number=household_number, slum_id=slum_id, city_id=city_id)
        if existing.exists():
            existing.update(rhs_data=rhs_data, submission_date=submission_date, created_date=created_date)
            print(f"[updated] household {household_number} (slum: {slum_name})")
        else:
            HouseholdData.objects.create(household_number=household_number, slum_id=slum_id, city_id=city_id, rhs_data=rhs_data, submission_date=submission_date, created_date=created_date)
            print(f"[created] household {household_number} (slum: {slum_name})")
        return True

    def fetch_subject_by_uuid(self, uuid: str) -> Optional[dict]:
        response = self._throttled_get(self.base_url + "api/subject/" + uuid, headers={"accept": "application/json", "AUTH-TOKEN": self.get_cognito_token()})
        if response.status_code != 200:
            logger.error("Subject fetch failed for %s: status %s", uuid, response.status_code)
            return None
        return json.loads(response.text)

    def _sync_one_uuid(self, row_num: int, total: int, uuid: str) -> str:
        """Runs on its own AvniHouseholdSync instance (see sync_subjects_by_uuid) so
        get_cognito_token()'s self.token/poolId/clientId state never gets shared
        between threads. Returns one of: saved / voided / fetch_failed / save_failed / errors.
        The whole body is one try/except -- a single timed-out or broken row
        (e.g. a slow/unresponsive Avni request) must not blow up as_completed()
        and abort the rest of a several-thousand-row batch."""
        print(f"[row {row_num}/{total}] fetching {uuid}")
        try:
            worker = AvniHouseholdSync()
            record = worker.fetch_subject_by_uuid(uuid)
            if not record:
                return "fetch_failed"
            if record.get("Voided"):
                print(f"[skipped] {uuid} is voided")
                return "voided"
            return "saved" if worker.save_subject_record(record) else "save_failed"
        except Exception as e:
            logger.error("Failed to sync %s: %s", uuid, e)
            return "errors"

    def sync_subjects_by_uuid(self, uuids, max_workers: int = 5) -> int:
        """Fetches and saves subject records given a list/iterable of subject UUIDs,
        running up to max_workers in parallel (each on its own AvniHouseholdSync instance)."""
        close_old_connections()
        rows = [(i, str(u).strip()) for i, u in enumerate(uuids, start=1)]
        total = len(rows)
        rows = [(i, u) for i, u in rows if u]
        empty = total - len(rows)

        counts = {"saved": 0, "voided": 0, "fetch_failed": 0, "save_failed": 0, "errors": 0}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._sync_one_uuid, row_num, total, uuid) for row_num, uuid in rows]
            for future in as_completed(futures):
                counts[future.result()] += 1
        close_old_connections()

        print(
            f"-- done: {counts['saved']}/{total} saved | "
            f"voided={counts['voided']} fetch_failed={counts['fetch_failed']} save_failed={counts['save_failed']} "
            f"errors={counts['errors']} empty_rows={empty} --"
        )
        return counts["saved"]

    def sync_subjects_from_excel(self, file_path: str, column: str = "uuid", max_workers: int = 5) -> int:
        """Reads a column of subject UUIDs from an Excel file and syncs each one via sync_subjects_by_uuid."""
        df = pd.read_excel(file_path)
        uuids = df[column].dropna().astype(str).tolist()
        return self.sync_subjects_by_uuid(uuids, max_workers=max_workers)

    def resolve_household_by_subject(self, subject_id: str) -> Optional[Tuple[str, str]]:
        response = self._throttled_get(self.base_url + "api/subject/" + subject_id, headers={"AUTH-TOKEN": self.get_cognito_token()})
        if response.status_code != 200:
            logger.error("Subject lookup failed for %s: status %s", subject_id, response.status_code)
            return None
        data = json.loads(response.text)
        observations = data.get("observations") or {}
        slum_name = (data.get("location") or {}).get("Slum")
        household_number = self.derive_household_number(observations.get("First name") or observations.get("first_name"))
        return (slum_name, household_number) if slum_name and household_number else None

    def save_encounter_record(self, record: dict, encounter_type: str) -> bool:
        observations = record.get("observations") or {}
        subject_id = record.get("Subject ID")
        if not observations or not subject_id:
            return False

        resolved = self.resolve_household_by_subject(subject_id)
        if not resolved:
            logger.error("Could not resolve household for %s encounter %s", encounter_type, record.get("ID"))
            return False
        slum_name, household_number = resolved

        try:
            slum_id, city_id = self.get_city_slum_ids(slum_name)
        except Exception as e:
            logger.error("Slum lookup failed for '%s': %s", slum_name, e)
            return False

        household = HouseholdData.objects.filter(household_number=household_number, slum_id=slum_id, city_id=city_id)
        if not household.exists():
            logger.error("No household found for %s/%s -- run subject sync first", slum_name, household_number)
            return False

        mapped = self.map_fields(observations)
        mapped["Last_modified_date"] = (record.get("audit") or {}).get("Last modified at")

        rhs_data = household.values_list("rhs_data", flat=True)[0] or {}
        rhs_data.update(mapped)
        household.update(rhs_data=rhs_data)
        print(f"[{encounter_type}] household {household_number} (slum: {slum_name})")
        return True

    def sync_subject(self, subject_type: str, last_modified_date_time: str = None, location_id: str = None, concepts=None, version: int = 1) -> int:
        page_data = self.fetch_page("api/subjects", "subjectType", subject_type, last_modified_date_time, location_id, concepts, version, 0)
        if not page_data:
            return 0

        total_pages, processed = page_data.get("totalPages", 1), 0
        for page_num in range(total_pages):
            if page_num:
                page_data = self.fetch_page("api/subjects", "subjectType", subject_type, last_modified_date_time, location_id, concepts, version, page_num)
            if not page_data:
                continue
            print(f"-- {subject_type} page {page_num + 1}/{total_pages} ({len(page_data.get('content', []))} records) --")
            for record in page_data.get("content", []):
                if record.get("Voided"):
                    continue
                try:
                    processed += int(self.save_subject_record(record))
                except Exception as e:
                    logger.error("Failed to save %s record %s: %s", subject_type, record.get("ID"), e)

        return processed

    def sync_encounter(self, encounter_type: str, last_modified_date_time: str = None, version: int = 1) -> int:
        page_data = self.fetch_page("api/encounters", "encounterType", encounter_type, last_modified_date_time, None, None, version, 0)
        if not page_data:
            return 0

        total_pages, processed = page_data.get("totalPages", 1), 0
        for page_num in range(total_pages):
            if page_num:
                page_data = self.fetch_page("api/encounters", "encounterType", encounter_type, last_modified_date_time, None, None, version, page_num)
            if not page_data:
                continue
            print(f"-- {encounter_type} page {page_num + 1}/{total_pages} ({len(page_data.get('content', []))} records) --")
            for record in page_data.get("content", []):
                if record.get("Voided"):
                    continue
                try:
                    processed += int(self.save_encounter_record(record, encounter_type))
                except Exception as e:
                    logger.error("Failed to save %s encounter %s: %s", encounter_type, record.get("ID"), e)

        return processed

    def sync_all_encounters(self, last_modified_date_time: str = None) -> dict:
        return {encounter_type: self.sync_encounter(encounter_type, last_modified_date_time) for encounter_type in ENCOUNTER_TYPES}

    def subject_summary(self, subject_type: str, location_id: str, last_modified_date_time: str = None, version: int = 1) -> dict:
        """Counts total / voided / not-voided records and ward distribution for a subject type at a location, without writing anything to the DB."""
        page_data = self.fetch_page("api/subjects", "subjectType", subject_type, last_modified_date_time, location_id, None, version, 0)
        if not page_data:
            return {"total": 0, "voided": 0, "not_voided": 0, "ward_distribution": {}}

        total_pages = page_data.get("totalPages", 1)
        total, voided, ward_distribution = 0, 0, {}

        for page_num in range(total_pages):
            if page_num:
                page_data = self.fetch_page("api/subjects", "subjectType", subject_type, last_modified_date_time, location_id, None, version, page_num)
            if not page_data:
                continue
            for record in page_data.get("content", []):
                total += 1
                if record.get("Voided"):
                    voided += 1
                    continue
                ward = (record.get("observations") or {}).get("Select Ward") or "Unknown"
                ward_distribution[ward] = ward_distribution.get(ward, 0) + 1

        return {"total": total, "voided": voided, "not_voided": total - voided, "ward_distribution": ward_distribution}

    # convenience wrappers -- thin aliases over sync_subject for readability
    def sync_structure_data(self, **kwargs) -> int:
        return self.sync_subject("Structure", **kwargs)

    def sync_dses_data(self, **kwargs) -> int:
        return self.sync_subject("Detailed Socio Economic Survey", **kwargs)

