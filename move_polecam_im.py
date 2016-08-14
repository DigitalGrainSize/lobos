#gets called by polecam.py to crop and fresize and image in a different processing
# makes tings faster
# daniel buscombe april 2016

from shutil import move as mv
from scipy.misc import imread, imsave
import sys, getopt

argv = sys.argv[1:]
filename = ''; outdirec = ''
opts, args = getopt.getopt(argv,"hi:o:")

for opt, arg in opts:
   if opt == '-h':
      print 'resize_n_move.py -i <filename> -o <outdirec>'
      sys.exit()
   elif opt in ("-i"):
      filename = arg
   elif opt in ("-o"):
      outdirec = arg

try:
    imsave(filename, imread(filename)[36:-36,58:-58,:])
    mv(filename,outdirec)
except:
   print "error"
