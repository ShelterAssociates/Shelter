# Shelter

Installing on Ubuntu

1. Clone the project 

  `git clone https://github.com/ShelterAssociates/Shelter.git`

2. Activate a python <a href='https://pypi.python.org/pypi/virtualenv'>virtualenv.</a>
 
   Create the new virtual environment `mkvirtualenv` or `workon` command and activate the environment before starting with installation.
   
   You can skip this step if you don't want to create a virtual environment.

3. Install postgressql server

  `apt-get install postgresql-server-dev-9.3`

4. Install python:

  `pip install -r requirement.txt`
  
5. Migrate the database

  `python manage.py syncdb`
  `python manage.py migrate`
  
6. Run the server

  `python manage.py runserver` 
  
  
