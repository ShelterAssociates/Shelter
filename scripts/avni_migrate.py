import pandas as pd
import numpy as np

base_path = "/home/amar/Documents/projects/shelter/Implementation/Kolhapur/"
df = pd.read_excel("/home/amar/Downloads/RHS_SBM_KMC.xlsx", sheet_name="RHS_SBM_KMC_v1")

def slum_registration():
	global df
	df=df.loc[df["Type of survey"]!="Follow-up survey"]
	cols = df.columns.tolist()
	df["Subject Type"]="Household"
	df["City"]="Kolhapur"
	df["Do you have addhar card?"] = np.where(df['Aadhar number']>0, 'Yes', 'No')
	df["First Name"]=df["Household number"]
	cols=['_id','Subject Type', 'First Name','City','admin_ward','slum_name','Name(s) of the surveyor(s)','Household number','Type of structure occupancy','Type of unoccupied house',
	'Parent household number','Full name of the head of the household','Enter the 10 digit mobile number','Do you have addhar card?', 'Aadhar number','Number of household members',
	'Total number of male members (including children)','Total number of female members (including children)','Type of structure of the house',
	'Ownership status of the house', 'House area in sq. ft.',]
	output = df[cols]
	rename_value={'City': 'City', 'Ownership status of the house': 'Ownership status of the house_1', 'Enter the 10 digit mobile number': 'Enter the 10 digit mobile number', 'Number of household members': 'Number of household members', 'House area in sq. ft.': 'House area in square feets.', 'Subject Type': 'Subject Type', 'Type of structure occupancy': 'Type of structure occupancy_1', 'Total number of female members (including children)': 'Total number of female members (including children)', 'Type of structure of the house': 'Type of structure of the house_1', 'Aadhar number': 'Aadhar number', 'Name(s) of the surveyor(s)': 'Name of the surveyor', 'Full name of the head of the household': 'Full name of the head of the household', 'Total number of male members (including children)': 'Total number of male members (including children)', 'Parent household number': 'Parent household number', 'slum_name': 'Slum', '_id': 'Id', 'admin_ward': 'Admin', 'Household number': 'Househhold number', 'Type of unoccupied house': 'Type of unoccupied house_1'}
	output=output.rename(columns=rename_value)
	output = output.sort_values(['Slum'],ascending = (False))
	output = output.replace(np.nan,'',regex=True)
	path = base_path + "slum_registration/"
	output=output.groupby('Slum')
	for slum_name, df_slum in output:
		df_slum.to_csv(path+'/'+str(slum_name).replace(' ','_')+'.csv', sep=',',encoding='utf-8', index=False)

def need_assessment():
	global df
	df=df.loc[df["Type of survey"]!="Follow-up survey"]
	df=df.loc[df["Type of structure occupancy"]=="Occupied house"]
	cols = df.columns.tolist()
	df["Encounter Type"]="Need Assessment"
	df["Id"] = df["_id"].astype(str) + 'N'
	df["_submission_time"] = pd.to_datetime(df["_submission_time"]).dt.strftime('%Y-%m-%d')
	df["Do you have individual water connection at home?"] = np.where(df['Type of water connection'].astype(str)=="Individual connection", 'Yes', 'No')
	df["Type of water connection ?"] = np.where(
		df['Type of water connection'].astype(str) == "Individual connection", '', df['Type of water connection'])
	df["Water source final answer."] = df['Type of water connection']
	df["Do you have a toilet at home?"] = np.where(df['Current_place_of_defecation'].isin(["01","02","03","04","05","06","07"]) ,'Yes','No')
	household_toilet = {5.0:"Own toilet", 7.0:"Toilet by SA", 4.0:"Toilet by any other agency", 1.0:"SBM (Installment)",
						2.0:"SBM (Contractor)",3.0:"Toilet by SA", 6.0:"Toilet by any other agency"}
	#df["Type of household toilet ?"] = np.where(df["Do you have a toilet at home?"].isin(["Yes"]), household_toilet[df['Current_place_of_defecation']]  ,'')
	df["Type of household toilet ?"] = df['Current_place_of_defecation'].map(household_toilet)
	cols=['_id','Encounter Type', "Id", "_submission_time","slum_name", "Household number", "Do you have individual water connection at home?",
		  "Type of water connection ?", "Water source final answer.","Do you dispose segregated garbage?",
		  "Do you have a toilet at home?","Do you have electricity in the house?","If yes for electricity; Type of meter",
		  "Does any household member have any of the construction skills given below?",
		  "Does any member of the household go for open defecation?", "Type of household toilet ?",
		  "What is the toilet connected to?", "Reason for not using toilet" , "Status of toilet under SBM",
		  "Who all use toilets in the household?","What was the cost incurred to build the toilet?"]
	output = df[cols]
	output["Does any household member have any of the construction skills given below?"] = np.where(output["Does any household member have any of the construction skills given below?"]!="Construction labour",output["Does any household member have any of the construction skills given below?"].replace(regex=[' '], value=','), output["Does any household member have any of the construction skills given below?"])
	rename_value={ '_submission_time':'Visit Date', '_id': 'Subject Id', 'slum_name':'Slum',
				   'Do you dispose segregated garbage?':'Do you segregated wet and dry garbage at source?',
				   'Facility of solid waste collection':'How do you dispose your solid waste ?',
				   'Do you have electricity in the house?':'Do you have electricity in the house ?',
				   'If yes for electricity; Type of meter':'If yes for electricity ,  type of meter ?',
				   'Does any household member have any of the construction skills given below?':'Does any household member have any of the construction skills given below ?',
				   'Does any member of the household go for open defecation?':'Does any member of the household go for open defecation ?',
				   'What is the toilet connected to?':'Where the individual toilet is connected to ?',
				   'Reason for not using toilet':'Reason for not using toilet ?',
				   'Status of toilet under SBM':'Status of toilet under SBM ?',
				   'Who all use toilets in the household?':'Who all use toilets in the household ?',
				   'What was the cost incurred to build the toilet?':'What was the cost incurred to build the toilet?'
				   }
	output=output.rename(columns=rename_value)
	output = output.sort_values(['Slum'],ascending = (False))
	output = output.replace(np.nan,'',regex=True)
	path = base_path + "need_assessment/"
	output=output.groupby('Slum')
	for slum_name, df_slum in output:
		df_slum.to_csv(path+'/'+str(slum_name).replace(' ','_')+'.csv', sep=';',encoding='utf-8', index=False,quoting=0)

#need_assessment()

def sanitation():
	global df
	df = df.loc[df["Type of survey"] != "Follow-up survey"]
	df = df.loc[df["Type of structure occupancy"] == "Occupied house"]
	cols = df.columns.tolist()
	df["Program"] = "Sanitation"
	df["Id"] = df["_id"].astype(str) + 'S'
	df["_submission_time"] = pd.to_datetime(df["_submission_time"]).dt.strftime('%Y-%m-%d')

	no_reason = ["Financial problems", "Small house","Tenant issue", "Lack of willingness", "Satisfied with the CTBs",
				 "Large family size", "Drainage related issues", "Others"]
	yes_reason = ["For safety of female members", "Unsatisfied with CTBs",
					  "For better convenience", "For elderly", "For handicapped", "For any member suffering from any illness",
					  "For better health and hygiene", "Other"]
	df = df.replace(np.nan, '', regex=True)
	def convert_multi_select(list_data, value):
		output = []
		for data in list_data:
			if data in value:
				output.append(data)
		return ','.join(output)

	def no_individual(value):
		return convert_multi_select(no_reason, value)

	def yes_individual(value):
		return convert_multi_select(yes_reason, value)

	df["If yes, why?"] = df["If yes, why?"].apply(yes_individual)
	df["If no, why?"] = df["If no, why?"].apply(no_individual)
	current_place = {1.0:"SBM (Installment)", 2.0:"SBM (Contractor)",
					 3.0:"Toilet by SA", 4.0:"Toilet by other NGO",
					 5.0:"Own toilet", 6.0:"Toilet by other NGO",
					 7.0:"Toilet by SA",
					 9.0:"Use CTB", 10.0:"Shared toilet",
					 11.0:"Public toilet outside slum", 12.0:"Open defecation",
					 13.0:"Non-functional, hence CTB",
					 14.0:"Group toilet", 15.0:"Use CTB of neighbouring slum", "":""}
	current_place_map = lambda x: current_place[x]

	df["Current place of defecation"] = df["Current_place_of_defecation"].map(current_place_map)

	installment_number ={0.0:'0',1.0:'1',2.0:'2',3.0:'3'}
	df["How many installments have you received?"] = df["How many installments have you received?"].map(installment_number)
	cols = ['_id', 'Program', "Id", "_submission_time", "slum_name", "Household number", "Have you applied for an individual toilet under SBM?",
			"Type of SBM toilets", "How many installments have you received?", "When did you receive your first installment?",
			"When did you receive your second installment?", "When did you receive your third installment?",
			"If built by contractor, how satisfied are you?", "Are you interested in an individual toilet?",
			"If yes, why?", "If no, why?", "What kind of toilet would you like?", "Under what scheme would you like your toilet to be built?",
			"Is there availability of drainage to connect to the toilet?","Current place of defecation"]
	output = df[cols]
	output = output.replace(np.nan, '', regex=True)
	rename_value = {'_submission_time': 'Enrolment Date', '_id': 'Subject Id', 'slum_name': 'Slum',
					'Have you applied for an individual toilet under SBM?':'Have you applied for an individual toilet under SBM?_1',
					'Type of SBM toilets':'Type of SBM toilets ?','How many installments have you received?':'How many installments have you received ?',
					'When did you receive your first installment?':'When did you receive your first SBM installment?',
					'When did you receive your second installment?':'When did you receive your second SBM installment?',
					'When did you receive your third installment?':'When did you receive your third SBM installment?',
					'If built by contractor, how satisfied are you?':'If built by contractor, how satisfied are you?',
					'Are you interested in an individual toilet?':'Are you interested in an individual toilet ?',
					'If yes, why?':'If yes for individual toilet , why?',
					'If no, why?':'If no for individual toilet , why?',
					'What kind of toilet would you like?':'What kind of toilet would you like ?',
					'Under what scheme would you like your toilet to be built?':'Under what scheme would you like your toilet to be built ?',
					'Is there availability of drainage to connect to the toilet?':'Is there availability of drainage to connect it to the toilet?'
					}
	output = output.rename(columns=rename_value)
	output = output.sort_values(['Slum'], ascending=(False))
	output = output.replace(np.nan, '', regex=True)
	path = base_path + "sanitation/"
	output = output.groupby('Slum')
	for slum_name, df_slum in output:
		df_slum.to_csv(path+'/'+str(slum_name).replace(' ','_')+'.csv', sep=',',encoding='utf-8', index=False,quoting=1)

sanitation()