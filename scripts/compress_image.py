"""
Compress script :  Compress all the image file that get collected in some folder

Input parameters 
	-h : help
	-f : folder path
	-s : (optional) files above this size will get compressed (in MBs)
	-q : (optional) Quality of image that needs to be maintained (in percentage)
	-c : (optional) If specified it will compress the image 
	     else just display the count. 
	    
"""
import os, ast
import sys
from PIL import Image
import argparse

def compressMe(filepath, quality):
	original_size = os.stat(filepath).st_size / 1024
	picture = Image.open(filepath)
	picture.save(filepath,  optimize=True, quality=quality)
	new_size = os.stat(filepath).st_size/1024
	print "original size -" + str(original_size) +" : new size -" + str(new_size) + " filepath::" + filepath


def getFiles(xml_root_path, above_size, quality, compress_flag):
	count = 0
	for dirpath, dirs, files in os.walk(xml_root_path):
		for filename in files:
			filepath = os.path.join(dirpath, filename)
			original_size = os.stat(filepath).st_size / 1024
			if original_size > above_size:
				if compress_flag:
					compressMe(filepath, quality)
				count += 1
	print "Total number of files greater that "+str(above_size)+"MB - " + str(count)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='compress_image', conflict_handler='resolve',
									description = "Script to compress all the image files in the specified folder")
	parser.add_argument('-f', '--folder', help='Folder path',required=True)
	parser.add_argument('-s', '--size', type=int, default=500, help='compress files above size(in MBs)')
	parser.add_argument('-q', '--quality', type=int, default=65, help='Quality to which the image needs to be compressed')
	parser.add_argument('-c', '--compress', action='store_true', help='Compress the files. If not supplied it will just print the count')
	args = parser.parse_args()
	if not args.help:
		folder_path = args.folder
		above_size = args.size
		quality = args.quality
		compress_flag = args.compress
		getFiles(folder_path, above_size, quality, compress_flag)



