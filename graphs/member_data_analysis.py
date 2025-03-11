from graphs.models import *
import pandas as pd
from django.db.models.functions import Cast
from django.db.models import CharField
from django.db.models import Max
from django.db.models import Count

class MemberDataProcess:
    updated_count = 0
    inserted_count = 0
    failed_count = 0
    error_logs = {}

    def __init__(self, slum):

        self.data = MemberData.objects.filter(slum_id = slum)
        self.program_data = MemberProgramData.objects.filter(slum_id = slum)
        self.encounter_data = MemberEncounterData.objects.filter(slum_id = slum)
        self.column_details = {'Are you a person with disability ?' : 'disability', 'Are you menstruating ?' : 'menstruation_status', 'Education' : 'education', 'Employment Status' : 'employment_status', 'How many Children do you have ?' : 'children_count', 'Marital Status' : 'marital_status', 'age' : 'age', 'created_date' : 'created_date', 'gender' : 'gender', 'household_number' : 'household_number', 'member_first_name' : 'member_first_name', 'submission_date' : 'submission_date', 'id' : 'id', 'slum_id__electoral_ward__administrative_ward__city__name__city_name' : 'city_name', 'slum_id' : 'slum_id', 'slum_id__name' : 'slum_name'}

    def convert_data_to_dict(self, data):
        return data.groupby('id').apply(lambda x: x.drop('id', axis=1).to_dict('records')[0]).to_dict()
    
    def create_member_metrics(self):
        # Extract member data and convert into dataframe for processing
        member_data = list(self.data.values('created_date', 'date_of_birth', 'gender', 'household_number', 'member_data', 'member_first_name', 'submission_date', 'slum_id', 'slum_id__name', 'id', "slum_id__electoral_ward__administrative_ward__city__name__city_name"))
        member_df = pd.DataFrame(member_data)
        # Convert date_of_birth column to datetime
        member_df['date_of_birth'] = pd.to_datetime(member_df['date_of_birth'], errors='coerce')
        # Checking if there are any nan values in date_of_birth_column ...
        if member_df['date_of_birth'].isnull().any():
            member_df = member_df[member_df['date_of_birth'].isnull() == False]
        # Cahculate age using date of birth.
        member_df['age'] = member_df['date_of_birth'].apply(lambda x: datetime.datetime.today().year - x.year - ((datetime.datetime.today().month, datetime.datetime.today().day) < (x.month, x.day)))
        # Drop date_of_birth column
        member_df = member_df.drop(columns=['date_of_birth'])
        # Map gender coding to categotical names.
        member_df['gender'] = member_df['gender'].map({'1' : 'Male', '2' : 'Female', '3' : 'Other'})
        # convert dataframe into list of dict
        member_data = member_df.to_dict(orient='records')
        member_data = [{**dct, **dct.pop("member_data")} for dct in member_data]
        member_df = pd.DataFrame(member_data, columns = ['Are you a person with disability ?', 'Are you menstruating ?', 'Education', 'Employment Status', 'How many Children do you have ?', 'Marital Status', 'age', 'created_date', 'gender', 'household_number', 'member_first_name',  'slum_id__name', 'submission_date', 'id', 'slum_id__electoral_ward__administrative_ward__city__name__city_name', 'slum_id'])
        member_df.rename(columns=self.column_details, inplace= True)
        return member_df
    
    def get_last_encounters(self, member_data, member_ids):
        # Get the most recent record for each member_id
        latest_records = self.encounter_data.filter(member_id__in = member_ids).values('member_id').annotate(
            latest_date=Max('submission_date'))
        # Get member IDs where the most recent encounter contains "Yes" for the given question
        qualified_members = self.encounter_data.filter(
            member_id__in=[rec['member_id'] for rec in latest_records],  # Filter only the latest records
            submission_date__in=[rec['latest_date'] for rec in latest_records],  # Ensure it's the latest
        )
        # Convert QuerySet to dictionary {member_id: query_object}
        qualified_members_dict = {record.member_id: record for record in qualified_members}
        # Utility function...
        def get_cup_use_status(id_):
            if id_ in qualified_members_dict:
                return qualified_members_dict[id_].cup_use_status
            return "No Record Available"
        member_data['cup_used_in_last_followup'] = member_data['id'].apply(get_cup_use_status)
        return member_data
    
    def create_member_program_metrics(self, member_data):
        # Extract member program data and convert into dataframe for processing
        member_ids = member_data['id'].tolist()
        member_program_data = list(self.program_data.filter(member_id__in = member_ids).values_list('member_id', flat = True))
        member_data['mhm_program_enrollment'] = member_data['id'].apply(lambda x: "Yes" if x in member_program_data else "No")
        # Query to count records for each member_id
        member_counts = self.encounter_data.values('member_id').annotate(encounter_count=Count('id'))
        # Convert to dictionary format
        member_count_dict = {record['member_id']: record['encounter_count'] for record in member_counts}
        # Map the counts to the 'id' column, default to 0 if not found
        member_data['available_followup_cnt'] = member_data['id'].map(member_count_dict).fillna(0).astype(int)
        # Checking cup used in last followup.
        member_data = self.get_last_encounters(member_data, member_ids)
        return member_data
    
    def save_member_data_metrics(self):
        """ETL function to process, insert, and update records while logging activity."""
        updated_count = 0
        inserted_count = 0
        failed_count = 0
        error_logs = {}
        
        # create member data matrices
        member_data_df = self.create_member_metrics()
        # create member program metrics
        self.create_member_program_metrics(member_data_df)
        # Convert dataframe into dict of rows
        final_data_for_update = self.convert_data_to_dict(member_data_df)
        # Create record_ids to fetch the model instences from the table.
        record_ids = list(final_data_for_update.keys())
        # Fetch the model instences using the above record_ids
        existing_records = {record.member_id : record for record in MemberDataETL.objects.filter(member_id__in=record_ids)}
        ''' Now Here we are have to handle two cases.
            1. Records that are available in our table. We have to update these records.
            2. Records that are not available in our table. We have to create new entries for these records
        '''
        # Separate records into updates and inserts
        records_to_update = []
        records_to_create = []
        # Loop to iterate on the final data
        for record_id, data in final_data_for_update.items():
            try:
                if record_id in existing_records:
                    # Update existing record
                    record = existing_records[record_id]
                    for field, value in data.items():
                        setattr(record, field, value)
                    records_to_update.append(record)
                    updated_count += 1
                else:
                    record = MemberDataETL(member_id = record_id, **data)
                    records_to_create.append(record)
                    inserted_count += 1
            except Exception as e:
                failed_count += 1
                error_logs[record_id] = str(e)

        # Perform bulk updates
        if records_to_update:
            MemberDataETL.objects.bulk_update(records_to_update, fields=final_data_for_update[record_ids[0]].keys())

        # Perform bulk inserts
        if records_to_create:
            MemberDataETL.objects.bulk_create(records_to_create)
        # Store ETL log
        return {'updated_records': updated_count, 'inserted_records' : inserted_count, 'failed_records' : failed_count, 'error_details' : error_logs}



# Running ETL Operations...

def main():
    list_of_slums = MemberData.objects.all().values_list('slum_id', flat = True).distinct() #[1362, 1091, 1253] #
    error_logs_dict = {'updated_records' : 0, 'inserted_records' : 0, 'failed_records' : 0, 'error_details' : {}}
    for slum_id in list_of_slums:
        mem_obj = MemberDataProcess(slum_id)
        etl_logs = mem_obj.save_member_data_metrics()
        error_logs_dict = { k: v + error_logs_dict.get(k) if isinstance(v, int) else {**error_logs_dict.get(k, {}), **v} for k, v in etl_logs.items()}
        print("*"*100)
        print(f"ETL completed for {slum_id}: {etl_logs['updated_records']} updated, {etl_logs['inserted_records']} inserted, {etl_logs['failed_records']} failed.")
    #Store ETL log
    ETLLog.objects.create(
        task_name = 'Member ETL Task',
        updated_records=error_logs_dict['updated_records'],
        inserted_records=error_logs_dict['inserted_records'],
        failed_records=error_logs_dict['failed_records'],
        error_details=error_logs_dict['error_details']
    )






