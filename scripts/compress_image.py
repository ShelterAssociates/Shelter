#Compress all jpg file found in kobo
import os
import sys
from PIL import Image

def compressMe(file, verbose=False):
	filepath = os.path.join(os.getcwd(), file)
	oldsize = os.stat(filepath).st_size
	picture = Image.open(filepath)
	dim = picture.size
	
	#set quality= to the preferred quality. 
	#I found that 85 has no difference in my 6-10mb files and that 65 is the lowest reasonable number
	picture.save("Compressed_"+file,"JPEG",optimize=True,quality=85) 
	
	newsize = os.stat(os.path.join(os.getcwd(),"Compressed_"+file)).st_size
	percent = (oldsize-newsize)/float(oldsize)*100
	if (verbose):
		print "File compressed from {0} to {1} or {2}%".format(oldsize,newsize,percent)
	return percent

def getFiles(xml_root_path):
	count = 0
	for dirpath, dirs, files in os.walk(xml_root_path):
		for filename in files:
			if os.stat(os.path.join(dirpath,filename)).st_size/1024 > 2048:
				count += 1
	print "Total number of files greater that 800 KB" + str(count)

if __name__ == "__main__":
	getFiles('')



