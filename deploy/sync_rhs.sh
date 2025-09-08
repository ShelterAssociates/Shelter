
python3 manage.py shell <<ORM
import graphs.sync_avni_data_copy as sync_module
from importlib import reload
reload(sync_module)
a = sync_module.avni_sync()
a.SaveRhsData("Structure")  # now it will work

#print(a.get_cognito_token())
#a.subject_data_update('Sheet1')


ORM
~     
