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
	household_toilet = {"05":"Own toilet", "07":"Toilet by SA", "04":"Toilet by any other agency", "01":"SBM (Installment)",
						"02":"SBM (Contractor)","03	":"Toilet by SA", "06":"Toilet by any other agency"}
	#df["Type of household toilet ?"] = np.where(df["Do you have a toilet at home?"].isin(["Yes"]), household_toilet[df['Current_place_of_defecation']]  ,'')
	df["Type of household toilet ?"] = df['Current_place_of_defecation'].map(household_toilet)
	cols=['_id','Encounter Type', "Id", "_submission_time", "Do you have individual water connection at home?",
		  "Type of water connection ?", "Water source final answer.","slum_name", "Do you dispose segregated garbage?",
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
		df_slum.to_csv(path+'/'+str(slum_name).replace(' ','_')+'.csv', sep=',',encoding='utf-8', index=False,quoting=1)

need_assessment()