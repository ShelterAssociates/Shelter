'''
Script to fetch tags and add that into another group.
Reads xml fille as string and using string operations replaced certain fields.
'''
import os
import uuid

path ='scripts/old_data_migration_to_xml/xml_output/Pune/Rapid Infrastructure Mapping(RIM)_old/'
file_paths = []

#All files from the path defined
for dirpath, dirs, files in os.walk(path):
	for filename in files:
		if filename.endswith('.xml'):
			file_paths.append(os.path.join(dirpath, filename))

for file_name_RA in file_paths:
    #read the file
	fp = open(file_name_RA,'r')
	s= fp.read()

    #Find admin_ward
	c1 = s.find('<group_ws5ux48><admin_ward>')
	if c1<10:
		print(file_name_RA)
	initial = s[c1+15:c1+79]
	print(initial)
	s=s.replace(initial, '')

    #Find the path where you need to insert admin ward
	c2 = s.find('<group_zl6oo94><group_uj8eg07>')
	second = s[c2:c2+30]
	s=s.replace(second,second+initial)

	#Update instanceID and add deprecatedID
	c3 = s.find('<meta><instanceID>')
	instance = s[c3:c3+79]
	instance = instance.replace('instanceID','deprecatedID')
	instance = instance.replace('<meta>','<meta><instanceID>uuid:'+str(uuid.uuid4())+'</instanceID>')
	s = s.replace(s[c3:c3+79], instance)

    #Write data back to file
	fp = open(file_name_RA,'w')
	fp.write(s)
	fp.close()