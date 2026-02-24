from reports.models import (
	Deliverable,
	WorkProgressParameter,
	BeneficiaryIndicator
)

# -------------------------------------------------
# SEED DELIVERABLES
# -------------------------------------------------

deliverables = [
	(
		"Spatial Mapping",
		"Systematic mapping and documentation of physical structures within the project area, including households and community assets.",
	),
	(
		"One Home One Toilet",
		"Ensuring access to individual household toilets by tracking the number of toilets constructed or made functional.",
	),
	(
		"Menstrual Hygiene Management",
		"Awareness and distribution of menstrual hygiene products, including tracking the number of menstrual cups distributed.",
	),
	(
		"Community Mobilization",
		"Community engagement activities conducted to raise awareness, encourage participation, and promote collective action.",
	),
]

for name, description in deliverables:
	try:
		Deliverable.objects.get(name=name)
	except Deliverable.DoesNotExist:
		obj = Deliverable(
			name=name,
			description=description
		)
		obj.save()


# -------------------------------------------------
# SEED WORK PROGRESS PARAMETERS
# -------------------------------------------------

work_progress_parameters = [
	(
		"Total Agreements",
		"Count",
		"Total number of agreements signed with households or beneficiaries during the reporting month.",
	),
	(
		"Material Distributed Households",
		"Households",
		"Number of households that received construction or sanitation-related materials during the reporting month.",
	),
	(
		"Toilets Completed",
		"Count",
		"Number of household toilets fully constructed and made functional during the reporting month.",
	),
	(
		"Toilets Under Construction",
		"Count",
		"Number of household toilets that are currently under construction during the reporting month.",
	),
	(
		"Factsheets Assigned",
		"Count",
		"Number of household or beneficiary factsheets created or assigned during the reporting month.",
	),
	(
		"Mobilization Activities Conducted",
		"Count",
		"Number of community mobilization activities conducted during the reporting month.",
	),
	(
		"Total Members Attended Mobilization",
		"Members",
		"Total number of community members who attended mobilization or awareness activities during the reporting month.",
	),
]

for name, unit, description in work_progress_parameters:
	try:
		WorkProgressParameter.objects.get(name=name)
	except WorkProgressParameter.DoesNotExist:
		obj = WorkProgressParameter(
			name=name,
			unit=unit,
			description=description
		)
		obj.save()


# -------------------------------------------------
# SEED BENEFICIARY INDICATORS
# -------------------------------------------------

beneficiary_indicators = [
	(
		"Total Households Benefited",
		"Households",
		"Total number of distinct households that received direct project benefits during the reporting month.",
	),
	(
		"Total Individuals Benefited",
		"Individuals",
		"Total number of individual beneficiaries who received direct benefits from project activities during the reporting month.",
	),
	(
		"Female Beneficiaries",
		"Individuals",
		"Number of female beneficiaries who directly benefited from project activities during the reporting month.",
	),
	(
		"Disabled Beneficiaries",
		"Individuals",
		"Number of persons with disabilities who directly benefited from project activities during the reporting month.",
	),
	(
		"Children Beneficiaries",
		"Individuals",
		"Number of children who directly benefited from project activities during the reporting month.",
	),
	(
		"Senior Citizen Beneficiaries",
		"Individuals",
		"Number of senior citizens who directly benefited from project activities during the reporting month.",
	),
]

for name, unit, description in beneficiary_indicators:
	try:
		BeneficiaryIndicator.objects.get(name=name)
	except BeneficiaryIndicator.DoesNotExist:
		obj = BeneficiaryIndicator(
			name=name,
			unit=unit,
			description=description
		)
		obj.save()


print("✅ Reports master data seeding completed successfully.")
