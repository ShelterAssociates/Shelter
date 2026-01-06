# Encryption utility used to generate secure keys for BIRT reports
from component.cipher import *

# Django settings (used for MEDIA_ROOT and command templates)
from django.conf import settings

# Used for timestamps (folder names & DB updates)
from datetime import datetime

# Used to execute shell commands (BIRT report generation)
import subprocess

# OS utilities for path handling
import os

# Used for zipping folders and deleting directories safely
import shutil

# Used for parallel execution of multiple report commands
from concurrent import futures


# Folder name under MEDIA_ROOT where FF reports are stored
ZIP_PATH = 'FFReport'


def report_exec(cmd):
	"""
	Executes a single shell command.
	This is used to generate one PDF using BIRT.
	Runs inside a thread from ThreadPoolExecutor.
	"""
	try:
		p = subprocess.Popen(
			cmd,
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
		)
		out, err = p.communicate()
		return out, err
	except Exception as e:
		# In case command execution fails
		return None, str(e)


class FFReport(object):
	"""
	Class responsible for generating Family Factsheet (FF) reports.
	- Generates individual household PDFs
	- Zips them into one file
	- Saves zip path in database
	"""

	def __init__(self, record_id):
		"""
		record_id is SponsorProjectDetailsSubFields instance
		"""
		self.project_detail = record_id

	def generate(self):
		"""
		Main method that:
		1. Creates folders
		2. Generates PDFs via BIRT
		3. Zips PDFs
		4. Cleans temporary files
		5. Updates database
		"""

		# Cipher used to encrypt parameters passed to BIRT
		cipher = AESCipher()

		# Fetch slum linked to this sponsor project
		obj_slum = self.project_detail.sponsor_project_details.slum

		# Fetch sponsor (organization & user)
		logged_sponsor = self.project_detail.sponsor_project_details.sponsor_project.sponsor

		# List of household codes sponsored
		sponsored_household = self.project_detail.household_code

		# Slum code used in report generation
		rp_slum_code = str(obj_slum.shelter_slum_code)

		# Sub-folder name format:
		# <SLUMCODE>_<NO_OF_HOUSEHOLDS>_<TIMESTAMP>
		# Example: 2721_45_20260106_121530
		sub_folder = "{}_{}_{}".format(
			rp_slum_code,
			len(sponsored_household),
			datetime.now().strftime("%Y%m%d_%H%M%S")
		)

		# Organization name used as folder (spaces replaced)
		org_name = str(logged_sponsor.organization_name).replace(' ', '_')

		# Base folder:
		# MEDIA_ROOT/FFReport/<ORG_NAME>
		base_folder = os.path.join(
			settings.MEDIA_ROOT,
			ZIP_PATH,
			org_name
		)

		# Final working folder:
		# MEDIA_ROOT/FFReport/<ORG_NAME>/<SUB_FOLDER>
		final_folder = os.path.join(base_folder, sub_folder)

		# Create folders safely (creates parents if missing)
		os.makedirs(final_folder, exist_ok=True)

		# List to store all BIRT commands
		execute_command = []

		# Generate one BIRT command per household
		for household_code in sponsored_household:
			# Encrypted key passed to BIRT report
			# Format: slum_code|household_code|user_id
			key = cipher.encrypt(
				str(rp_slum_code) + '|' +
				str(household_code) + '|' +
				str(logged_sponsor.user.id)
			)

			# Output PDF path for this household
			pdf_file = os.path.join(
				final_folder,
				"household_code_{}.pdf".format(household_code)
			)

			# Final BIRT command using Django setting
			cmd = settings.BIRT_REPORT_CMD.format(pdf_file, key)

			# Add command to list
			execute_command.append(cmd)

		# Execute BIRT commands in parallel (max 3 at a time)
		try:
			with futures.ThreadPoolExecutor(max_workers=3) as executor:
				list(executor.map(report_exec, execute_command))
		except Exception as e:
			print(e)

		# Create ZIP of the entire folder
		# Resulting file: <final_folder>.zip
		zip_file_path = shutil.make_archive(
			final_folder,
			'zip',
			final_folder
		)

		# Remove temporary PDF folder safely
		shutil.rmtree(final_folder, ignore_errors=True)

		# If an old zip exists in DB, delete it from storage
		if self.project_detail.zip_file and self.project_detail.zip_file.name:
			self.project_detail.zip_file.delete(save=False)

		# Update DB with new zip file path and timestamp
		# Path must be RELATIVE to MEDIA_ROOT
		self.project_detail.__class__.objects.filter(
			pk=self.project_detail.id
		).update(
			zip_created_on=datetime.now(),
			zip_file=os.path.join(
				ZIP_PATH,
				org_name,
				sub_folder + '.zip'
			)
		)
