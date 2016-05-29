from glob import glob
import matplotlib.pyplot as plt
from numpy import genfromtxt, asarray, flipud, rot90
from scipy.misc import imread

images = glob('C:\lobos\eyeballimages\*.png')

E=[]
N=[]
for image in images:
    N.append(image.split('.png')[0].split('_')[-1])
    E.append(image.split('_')[-2])

imagefile = 'C:\lobos\sonar_boat_tiffs\cm_2016_rm1_600dpi.png'
tfwfile = 'C:\lobos\sonar_boat_tiffs\cm_2016_rm1_600dpi.pgw'

pil_image = imread(imagefile)
pos = genfromtxt(tfwfile)
x,y,d = pil_image.shape

imextent=[ pos[4], pos[4]+y*pos[0], pos[5]-x*pos[0], pos[5] ]

xx=[241036.144,
240913.685,
241029.634,
240598.639,
240122.409,
240138.593,
239986.578,
239986.468,
240096.053,
240153.89]

yy=[649322.109,
649063.755,
648956.733,
648786.891,
648730.618,
648023.319,
647903.42,
647866.597,
647856.01,
647440.328,
]

plt.imshow(pil_image,extent=imextent)
plt.plot(asarray(E, dtype='float'),asarray(N, dtype='float'),'ks')
plt.plot(xx,yy,'ro',markersize=16)
plt.plot(239697.658, 649623.930, 'ms')

plt.show()
