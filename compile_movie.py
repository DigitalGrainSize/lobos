
import matplotlib.animation as animation
import matplotlib.pyplot as plt
from scipy.misc import imread
import glob, os, time
import sys, getopt

argv = sys.argv[1:]
FPS = '' ; tag = ''
opts, args = getopt.getopt(argv,"hi:t:")

for opt, arg in opts:
   if opt == '-h':
      print 'resize_n_move.py -i <fps> - t <tag>'
      sys.exit()
   elif opt in ("-i"):
      FPS = arg
   elif opt in ("-t"):
      tag = arg

FPS = int(FPS)

now = time.asctime().replace(' ','_').replace(':','_')

infiles = sorted(glob.glob(os.path.join(os.getcwd(),'videos')+os.sep+'*'+tag+'*.png'))

fig = plt.figure()
fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)

ax = fig.add_subplot(111)
ax.get_xaxis().set_visible(False)
ax.get_yaxis().set_visible(False)

im = ax.imshow(imread(infiles[0]), aspect='auto')

def initmov():
   im.set_data([[]])
   return im

def update_img(i):
    im.set_data(imread(infiles[i]))

    #ext = os.path.splitext(infiles[i])[1][1:]
    #date = infiles[i].split(os.sep)[-1].split('RC')[-1].split('_')[1]
    #time = infiles[i].split(os.sep)[-1].split('RC')[-1].split('_')[2].split('.'+ext)[0]

    #plt.title(DT.datetime.strptime(date+' '+time, '%Y%m%d %H%M').strftime('%d %b %Y, %H:%M'))
    #plt.title(infiles[i].split(os.sep)[-1].split('.')[0])
    return im

ani = animation.FuncAnimation(fig,update_img, frames=len(infiles), interval=100, init_func = initmov, save_count=len(infiles))
# print('using ffmpeg to compile video')
writer = animation.writers['ffmpeg']()#(fps=FPS)

ani.save(os.path.expanduser("~")+os.sep+now+'.mp4',writer=writer,dpi=600)
del fig

for imfile in infiles:
    os.remove(imfile)
