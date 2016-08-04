import psycopg2

def main():
    Slum()
    pass

def AW():
    old = psycopg2.connect(database='old1',user='postgres',password='softcorner',host='localhost',port='5432')
    cursor_old = old.cursor()
    cursor_old.execute("select * from  slum_data_administrativeward where ward_number in (select id from slum_data_administrativeward where city_id=1)")
    fetch_data = cursor_old.fetchall()
    for f in fetch_data:
        id = f[0]
        name = f[1]
        ward_number=f[2]
        description = f[3]
        office_address = f[4]
        shape = f[7]
        shelter = psycopg2.connect(database='shelter',user='postgres',password='softcorner',host='localhost',port='5432')
        cursor_shelter_insert = shelter.cursor()
        query = "insert into master_administrativeward (id,city_id,name,shape,ward_no,description,office_address) VALUES (%s,%s, %s, %s, %s, %s ,%s);"
        data = (id,'1',name,shape,ward_number,description,office_address)
        cursor_shelter_insert.execute(query,data)
        shelter.commit()


def WOC():
    old = psycopg2.connect(database='old1',user='postgres',password='softcorner',host='localhost',port='5432')
    cursor_old = old.cursor()
    cursor_old.execute("select id,name,administrative_ward_id  from slum_data_wardofficer;")
    print "Hello"
    fetch_data1 = cursor_old.fetchall()
    for f in fetch_data1:
        administrative_ward = f[2]
	print administrative_ward
        name = f[1]
        print name  
        id = f[0]  
        print id
        shelter = psycopg2.connect(database='shelter',user='postgres',password='softcorner',host='localhost',port='5432')
        cursor_shelter_insert = shelter.cursor()
        query = "insert into master_wardofficecontact (administrative_ward_id,name,title,telephone) VALUES (%s, %s ,%s ,%s) ;"
	
        data = (administrative_ward,name,"","")
	print data
        cursor_shelter_insert.execute(query,data)
        shelter.commit()
        print ("finished")


def EW():
    old = psycopg2.connect(database='old1',user='postgres',password='softcorner',host='localhost',port='5432')
    cursor_old = old.cursor()
    cursor_old.execute("select *from slum_data_electoralward where administrative_ward_id in (select id from slum_data_administrativeward where city_id=1);")
    fetch_data1 = cursor_old.fetchall()
    for f in fetch_data1:
        id = f[0]
        administrative_ward_id = f[4] 
        name = f[1]
        shape = f[5]
        ward_no =  f[3]
        ward_code = "NA"
        extra_info = "NA"
        shelter = psycopg2.connect(database='shelter',user='postgres',password='softcorner',host='localhost',port='5432')
        cursor_shelter_insert = shelter.cursor()
        query = "insert into master_ElectoralWard (id,administrative_ward_id,name,shape,ward_no,ward_code,extra_info) VALUES (%s, %s ,%s ,%s, %s, %s, %s) ;"
        data = (id,administrative_ward_id,name,shape,ward_no,ward_code,extra_info)
        cursor_shelter_insert.execute(query,data)
        shelter.commit()


"""
def Slum():
    old = psycopg2.connect(database='old1',user='postgres',password='softcorner',host='localhost',port='5432')
    cursor_old = old.cursor()
    cursor_old.execute("select * from slum_data_slum where city_id=1;")
    fetch_data1 = cursor_old.fetchall()
    for f in fetch_data1:
        id = f[0]
        electoral_ward_id = 
        name = f[1]
        shape = f[7]
        description = f[2] 
        shelter_slum_code = "NA"
        shelter = psycopg2.connect(database='shelter',user='postgres',password='softcorner',host='localhost',port='5432')
        cursor_shelter_insert = shelter.cursor()
        query = "insert into master_slum (id,electoral_ward_id,name,shape,description,shelter_slum_code) VALUES (%s ,%s ,%s, %s, %s, %s) ;"
        data = (id,electoral_ward_id,name,shape,description,shelter_slum_code)
        cursor_shelter_insert.execute(query,data)
        shelter.commit()
"""



def Slum():
    old = psycopg2.connect(database='old1',user='postgres',password='softcorner',host='localhost',port='5432')
    old_insert = old.cursor()
    old_insert.execute("select * from slum_data_slum where city_id=1;")
    fetch_data = old_insert.fetchall()
    for f in fetch_data:
        id = f[0]
        iid = str(id)
        name = f[1]
        description = f[2]
        shape = f[6]
        shelter_slum_code = "NIL"
        old2 = psycopg2.connect(database='old1',user='postgres',password='softcorner',host='localhost',port='5432')
        cursor_old2 = old2.cursor()
        query1 = "select electoralward_id from info where slum_id =%s;"
        data = (iid,)
        cursor_old2.execute(query1,data)
        fetch_data2 = cursor_old2.fetchone()
        electoralward_id = 0
        print type(fetch_data2[0])
        electoral_ward_id=fetch_data2[0]
        if electoralward_id == "NIL":
            electoralward_id = 0#print electoral_ward_id
        old2.commit()
        shelter = psycopg2.connect(database='shelter',user='postgres',password='softcorner',host='localhost',port='5432')
        cursor_shelter_insert = shelter.cursor()
        query = "insert into master_slum (id,electoral_ward_id,name,shape,description,shelter_slum_code) VALUES (%s ,%s ,%s, %s, %s, %s) ;"
        data = (id,electoral_ward_id,name,shape,description,shelter_slum_code)
        cursor_shelter_insert.execute(query,data)
        shelter.commit()

    








"""

old_insert = old.cursor()
>>> old_insert.execute("select * from slum_data_slum where city_id=1;")  
>>> fetch_data = old_insert.fetchall()
>>> for f in fetch_data: 
...     id = f[0]
...     iid = str(id)
...     old2 = psycopg2.connect(database='old1',user='postgres',password='softcorner',host='localhost',port='5432')
...     cursor_old2 = old2.cursor()
...     query1 = "select electoralward_id from info where slum_id =%s;"
...     data = (iid,) 
...     cursor_old2.execute(query1,data)
...     p=cursor_old2.fetchone()
...     print p

"""











    
if __name__ == "__main__":
    main()
