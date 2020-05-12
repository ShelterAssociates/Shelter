import pandas as pd
import numpy as np

df = pd.read_excel("~/Downloads/RHS_SBM_KMC.xlsx", sheet_name="RHS_SBM_KMC_v1")
df=df.loc[df["Type of survey"]!="Follow-up survey"]
cols = df.columns.tolist()
df["Subject Type"]="Household"
df["City"]="Kolhapur"
df["Do you have addhar card?"] = np.where(df['Aadhar number']!="", 'Yes', 'No')
cols=['_id','Subject Type', 'Household number','City','admin_ward','slum_name','Name(s) of the surveyor(s)','Household number','Type of structure occupancy','Type of unoccupied house',
    'Parent household number','Full name of the head of the household','Enter the 10 digit mobile number','Aadhar number','Number of household members',
    'Total number of male members (including children)','Total number of female members (including children)','Type of structure of the house',
    'Ownership status of the house', 'House area in sq. ft.',]
output = df[cols]
rename_value={'City': 'City', 'Ownership status of the house': 'Ownership status of the house_1', 'Enter the 10 digit mobile number': 'Enter the 10 digit mobile number', 'Number of household members': 'Number of household members', 'House area in sq. ft.': 'House area in square feets.', 'Subject Type': 'Subject Type', 'Type of structure occupancy': 'Type of structure occupancy_1', 'Total number of female members (including children)': 'Total number of female members (including children)', 'Type of structure of the house': 'Type of structure of the house_1', 'Aadhar number': 'Aadhar number', 'Name(s) of the surveyor(s)': 'Name of the surveyor', 'Full name of the head of the household': 'Full name of the head of the household', 'Total number of male members (including children)': 'Total number of male members (including children)', 'Parent household number': 'Parent household number', 'slum_name': 'Slum', '_id': 'Id', 'admin_ward': 'Admin', 'Household number': 'Househhold number', 'Type of unoccupied house': 'Type of unoccupied house_1'}
output=output.rename(columns=rename_value)
output = output.sort_values(['Slum'],ascending = (False))
output = output.replace(np.nan,'',regex=True)
path = "~/Documents/projects/shelter/Implementation/Kolhapur/"
output=output.groupby('Slum')
for slum_name, df_slum in output:
	df_slum.to_csv(path+'/'+str(slum_name).replace(' ','_')+'.csv', sep=';', encoding='utf-8', index=False)