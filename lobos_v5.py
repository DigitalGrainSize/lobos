"""
lobos_v3.py
program to
1) view and capture an image of sediment
2) get site info from the user
3) save image to file with the site and time in the file name

Written by:
Daniel Buscombe, March 2015, updated June 2015, December 2015
then a major rewrite in April 2016
Grand Canyon Monitoring and Research Center, U.G. Geological Survey, Flagstaff, AZ
please contact:
dbuscombe@usgs.gov

SYNTAX:
python lobos_v3.py

REQUIREMENTS:
python
kivy (http://kivy.org/#home)
pyserial
pynmea
pyproj
matplotlib
numpy
scipy
"""

# import kivy related libraries
import kivy
kivy.require('1.9.1')

from kivy.lang import Builder
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from kivy.uix.accordion import *
from kivy.properties import *
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.graphics import Canvas, Translate, Fbo, ClearColor, ClearBuffers
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock

# this allows the program to boot into fullscreen mode
from kivy.config import Config
Config.set('graphics', 'fullscreen', 1) #1 == go fullscreen
Config.write()

#import other libraries
import time, os
os.environ['COMSPEC']

import subprocess
from shutil import move as mv
import serial
from pynmea import nmea
import pyproj
import ConfigParser
import matplotlib.pyplot as plt
from scipy.misc import imread
from numpy import genfromtxt

import matplotlib as mpl
import matplotlib.pyplot as plt
from kivy_matplotlib import MatplotFigure

#============= START config =====================================
# read the configuration file
config = ConfigParser.RawConfigParser()
config.read('lobos.cfg')

# # com-number for serial port gps
COMNUM = config.getint('lobos', 'gpscom')
# # com-number for serial port camera
COMNUM2 = config.getint('lobos', 'camcom')
# # com-number for echosounder
COMNUM3 = config.getint('lobos', 'soundercom')

# #same baud rate for gps
BAUDRATE = config.getint('lobos', 'gpsbaud')
# #set baud rate for caemra
BAUDRATE2 = config.getint('lobos', 'cambaud')
# #baud rate for echosounder
BAUDRATE3 = config.getint('lobos', 'sounderbaud')

cs2cs_args = config.get('lobos', 'cs2cs_args')
# get the transformation matrix of desired output coordinates
try:
   trans =  pyproj.Proj(init=cs2cs_args)
except:
   trans =  pyproj.Proj(cs2cs_args)

# if true, create an html map for online rendering in a web browser
MAKEMAP = config.getboolean('lobos', 'makemap')
if MAKEMAP:
    try:
        import folium
    except:
        MAKEMAP=False

# if true, will show map on screen
SHOWMAP = config.getboolean('lobos', 'showmap')
# this is the tif wirld file
TFWFILE = os.path.normpath(os.path.join(os.getcwd(),'sonar_boat_tiffs',config.get('lobos', 'tfwfile')))
# this is the background image file
IMAGEFILE = os.path.normpath(os.path.join(os.getcwd(),'sonar_boat_tiffs',config.get('lobos', 'imagefile')))
# this is the extent in metres of the box around the last measurement
IMBOX_X = config.getint('lobos', 'imbox_x')
# this is the extent in metres of the box around the last measurement
IMBOX_Y = config.getint('lobos', 'imbox_y')

STATION_START = config.getint('lobos', 'station_start')

#============= END config =====================================

#=========================
def init_fig(self,IMAGEFILE, TFWFILE):
    '''initialise real time display figure
    '''
    pil_image = imread(IMAGEFILE)
    pos = genfromtxt(TFWFILE)
    x,y,d = pil_image.shape

    self.starttime = time.mktime(time.localtime())
    if 'flag' in IMAGEFILE:
       #self.ax.imshow(pil_image,extent=[pos[0],pos[2],pos[1],pos[3]])
       self.fig.gca().imshow(pil_image,extent=[pos[0],pos[2],pos[1],pos[3]])
    elif 'lake' in IMAGEFILE:
       #self.ax.imshow(pil_image,extent=[pos[0],pos[2],pos[1],pos[3]])
       self.fig.gca().imshow(pil_image,extent=[pos[0],pos[2],pos[1],pos[3]])
    else:
        ##imextent=[ pos[4], pos[4]+x*pos[0], pos[5], pos[5]+y*pos[0] ]
        imextent=[ pos[4], pos[4]+y*pos[0], pos[5]-x*pos[0], pos[5] ]

        # self.ax.imshow(pil_image,extent=imextent) #[pos[0],pos[2],pos[1],pos[3]])
        self.fig.gca().imshow(pil_image,extent=imextent)
    self.fig.gca().axis('off')
    return self

#=========================
def init_serial3(self,portnum):
    '''initialise serial port for echosounder
    '''
    comnum = 'COM' + str(portnum)

    now = time.asctime().replace(' ','_').replace(':','_')

    try:
        global BAUDRATE3
        self.ser3 = serial.Serial()
        self.ser3.baudrate = BAUDRATE3
        self.ser3.port = comnum
        self.ser3.timeout = 0.5
        self.ser3.open()
        if self.ser3.isOpen():
            self.textinput.text += 'Echosounder opened on port '+str(portnum)+'\n'
            print '==========================='
            print 'Echosounder is open'
            print '==========================='
            self.echosounderopen = 1
    except:
        self.textinput.text += 'Echosounder failed to open on port '+str(portnum)+'\n'
        self.ser3 = 0
        print '==========================='
        print "Echosounder failed to open"
        print '==========================='
        self.echosounderopen = 0

    return self

#=========================
def init_serial2(self,portnum):
 '''initialise serial port for camera commands
 '''
 comnum = 'COM' + str(portnum)

 now = time.asctime().replace(' ','_').replace(':','_')
 try:
     global BAUDRATE2
     self.ser2 = serial.Serial()
     self.ser2.baudrate = BAUDRATE2
     self.ser2.port = comnum
     self.ser2.timeout = 0.5
     self.ser2.open()
     if self.ser2.isOpen():
        self.textinput.text += 'Camera serial opened on port '+str(portnum)+'\n'
        print '==========================='
        print 'Camera serial is open'
        print '==========================='
        self.camopen = 1
 except:
     self.textinput.text += 'Camera serial failed to open on port '+str(portnum)+'\n'
     self.ser2 = 0
     print '==========================='
     print "Camera serial failed to open"
     print '==========================='
     self.camopen = 0

 return self

#=========================
def init_serial(self,portnum):
 '''initialise serial port for gps
 '''
 comnum = 'COM' + str(portnum)

 now = time.asctime().replace(' ','_').replace(':','_')
 try:
     global BAUDRATE
     self.ser = serial.Serial()
     self.ser.baudrate = BAUDRATE
     self.ser.port = comnum
     self.ser.timeout = 0.5
     self.ser.open()
     if self.ser.isOpen():
        self.textinput.text += 'GPS opened on port '+str(portnum)+'\n'
        print '==========================='
        print 'GPS is open'
        print '==========================='
        self.gpsopen = 1
 except:
     self.textinput.text += 'GPS failed to open on port '+str(portnum)+'\n'
     self.ser = 0
     print '==========================='
     print "GPS failed to open"
     print '==========================='
     self.gpsopen = 0

 return self

#=========================
def get_nmea(self):
    '''get easting/northing from serial port gps
    '''

    gotpos = 0; counter = 0
    while (gotpos==0) &(counter<1):
       line = self.ser.read(400) # read 400 bytes
       parts = line.split('\r\n') # split by line return

       gpgga_parts = []; gprmc_parts = [];
       newparts = [] # create new variable which contains cleaned strings
       for k in range(len(parts)):
          if parts[k].startswith('$'): #select if starts with $
             if len(parts[k].split('*'))>1: #select if contains *
                if parts[k].count('$')==1: # select if only contains 1 $
                    newparts.append(parts[k])

       for k in range(len(newparts)):
         if "GPGGA" in newparts[k]:
            gpgga_parts.append(newparts[k])
         elif "GPRMC" in newparts[k]:
            gprmc_parts.append(newparts[k])

       if gpgga_parts:
          gotpos=1
          gpgga_parts = gpgga_parts[-1];
       if gprmc_parts:
          gprmc_parts = gprmc_parts[-1];

       counter += 1

    gpgga = nmea.GPGGA();
    gprmc = nmea.GPRMC();

    # GPGGA
    try:
        gpgga.parse(gpgga_parts)
        lats = gpgga.latitude
        longs= gpgga.longitude

        #convert degrees,decimal minutes to decimal degrees
        lat1 = (float(lats[2]+lats[3]+lats[4]+lats[5]+lats[6]+lats[7]+lats[8]))/60
        lat = (float(lats[0]+lats[1])+lat1)
        long1 = (float(longs[3]+longs[4]+longs[5]+longs[6]+longs[7]+longs[8]+longs[9]))/60
        long = (float(longs[0]+longs[1]+longs[2])+long1)

        #convert to az central state plane east/north
        e,n = trans(-long,lat)
    except:
        # GPRMC
        try:
            gprmc.parse(gprmc_parts)
            lats = gprmc.lat; longs= gprmc.lon

            #convert degrees,decimal minutes to decimal degrees
            lat1 = (float(lats[2]+lats[3]+lats[4]+lats[5]+lats[6]+lats[7]+lats[8]))/60
            lat = (float(lats[0]+lats[1])+lat1)
            long1 = (float(longs[3]+longs[4]+longs[5]+longs[6]+longs[7]+longs[8]+longs[9]))/60
            long = (float(longs[0]+longs[1]+longs[2])+long1)

            #convert to az central state plane east/north
            e,n = trans(-long,lat)

        except:
            n = self.n_txt.text
            e = self.e_txt.text


    return str(e), str(n), -long, lat

#=========================
def get_nmeadepth(self):
    '''get nmea depth from serial port echosounder
    '''

    try:
       depth_ft = self.ser3.read(300).split('DBT')[1].split(',f,')[0].split(',')[1]
       d = str(float(depth_ft)*0.3048)

    except:
       d = 'NaN'

    return d

#=========================
#=========================
def export_to_png(self, filename, *args):
    '''Saves an image of the widget and its children in png format at the
    specified filename. Works by removing the widget canvas from its
    parent, rendering to an :class:`~kivy.graphics.fbo.Fbo`, and calling
    :meth:`~kivy.graphics.texture.Texture.save`.
    '''

    if self.parent is not None:
        canvas_parent_index = self.parent.canvas.indexof(self.canvas)
        self.parent.canvas.remove(self.canvas)

    fbo = Fbo(size=self.size,  with_stencilbuffer=True)

    with fbo:
        ClearColor(0, 0, 0, 1)
        ClearBuffers()
        Translate(-self.x, -self.y, 0)

    fbo.add(self.canvas)
    fbo.draw()
    fbo.texture.save(filename, flipped=False)
    fbo.remove(self.canvas)

    if self.parent is not None:
        self.parent.canvas.insert(canvas_parent_index, self.canvas)

    return True

#=========================
## kv markup for building the app
Builder.load_file('lobos.kv')

#=========================
#=========================
class Log(TextInput):
    '''
    class that allows user to manually update station
    '''
    def on_double_tap(self):
        # make sure it performs it's original function
        super(Log, self).on_double_tap()

        def on_word_selection(*l):
            selected_word = self.selection_text
            print selected_word

        # let the word be selected wait for
        # next frame and get the selected word
        Clock.schedule_once(on_word_selection)

#=========================
#=========================
class CameraWidget(BoxLayout):
    '''
    class that defines the camera widget
    and interacts with the buttons in the app (takes images, sets modes, etc)
    '''
    #=========================
    def Play(self, *args):
       if self.ids.camera.play == True:
           self.ids.camera.play = False
           now = time.asctime() #.replace(' ','_')
           self.textinput.text += 'Video paused '+now+'\n'
       else:
           self.ids.camera.play = True
           now = time.asctime() #.replace(' ','_')
           self.textinput.text += 'Video resumed '+now+'\n'

    #=========================
    def TakePicture(self, fig, mode):#*args):
        '''takes a picture and saves it to the folder according to 'mode'
        '''
        self.export_to_png = export_to_png

        tmp = Clipboard.paste()
        self.n_txt.text = tmp.split(':')[0]
        self.e_txt.text = tmp.split(':')[1]

        now = time.asctime().replace(' ','_').replace(':','_')

        if mode==1:
            filename = 'st'+self.txt_inpt.text+'_sand_'+now+'_'+self.e_txt.text+'_'+self.n_txt.text+'.png'
        elif mode==2:
            filename = 'st'+self.txt_inpt.text+'_gravel_'+now+'_'+self.e_txt.text+'_'+self.n_txt.text+'.png'
        elif mode==3:
            filename = 'st'+self.txt_inpt.text+'_rock_'+now+'_'+self.e_txt.text+'_'+self.n_txt.text+'.png'
        elif mode==4:
            filename = 'st'+self.txt_inpt.text+'_sandrock_'+now+'_'+self.e_txt.text+'_'+self.n_txt.text+'.png'
        elif mode==5:
            filename = 'st'+self.txt_inpt.text+'_sandgravel_'+now+'_'+self.e_txt.text+'_'+self.n_txt.text+'.png'
        elif mode==6:
            filename = 'st'+self.txt_inpt.text+'_gravelsand_'+now+'_'+self.e_txt.text+'_'+self.n_txt.text+'.png'

        self.export_to_png(self.ids.camera, filename=filename)

        if mode==1:
            subprocess.Popen("python resize_n_move.py -i "+filename+" -o eyeballimages", shell=True)
            self.textinput.text += 'Sand image @ '+time.asctime().split(' ')[3]+'\n'
        elif mode==2:
            subprocess.Popen("python resize_n_move.py -i "+filename+" -o gravelimages", shell=True)
            self.textinput.text += 'Gravel image @ '+time.asctime().split(' ')[3]+'\n'
        elif mode==3:
            subprocess.Popen("python resize_n_move.py -i "+filename+" -o rockimages", shell=True)
            self.textinput.text += 'Rock image @ '+time.asctime().split(' ')[3]+'\n'
        elif mode==4:
            subprocess.Popen("python resize_n_move.py -i "+filename+" -o sandrockimages", shell=True)
            self.textinput.text += 'Sand/Rock image @ '+time.asctime().split(' ')[3]+'\n'
        elif mode==5:
            subprocess.Popen("python resize_n_move.py -i "+filename+" -o sandgravelimages", shell=True)
            self.textinput.text += 'Sand/Gravel image @ '+time.asctime().split(' ')[3]+'\n'
        elif mode==6:
            subprocess.Popen("python resize_n_move.py -i "+filename+" -o gravelsandimages", shell=True)
            self.textinput.text += 'Gravel/Sand image @ '+time.asctime().split(' ')[3]+'\n'

        if SHOWMAP:
            if mode==1:
                fig.gca().plot(float(self.e_txt.text),float(self.n_txt.text),'ys')
            elif mode==2:
                fig.gca().plot(float(self.e_txt.text),float(self.n_txt.text),'s',color=(.5,.5,.5))
            elif mode==3:
                fig.gca().plot(float(self.e_txt.text),float(self.n_txt.text),'rs')
            elif mode==4:
                fig.gca().plot(float(self.e_txt.text),float(self.n_txt.text),'s', color=(1.0, 0.6, 0.0))
            elif mode==5:
                fig.gca().plot(float(self.e_txt.text),float(self.n_txt.text),'s', color=(0.75, 0.6, 0.8))
            elif mode==6:
                fig.gca().plot(float(self.e_txt.text),float(self.n_txt.text),'s', color=(0.7, 0.7, 0.1))
            fig.canvas.draw()

    #=========================
    def change_st(self):
        '''
        changes station and prints to log
        '''
        self.textinput.text += 'Station is '+self.txt_inpt.text+'\n'

        # # get the last site visited and add 1, write to station file
        # fsite = open('station_start.txt','wb')
        # fsite.write(str(int(self.txt_inpt.text)+1))
        # fsite.close()
        countmax=16; counter=0
        with open('lobos.cfg','rb') as oldfile, open('lobos_new.cfg','wb') as newfile:
           for line in oldfile:
              counter += 1
              if counter==countmax:
                 #newfile.write("            text: '"+st+"'\n")
                 newfile.write('station_start = '+self.txt_inpt.text+'\n')
              else:
                 newfile.write(line)
        mv('lobos_new.cfg','lobos.cfg')

    #=========================
    def station_up(self):
        '''
        increment station 1
        '''
        if self.textinput.counter==0:
            self.textinput.foreground_color = (0.6,0.5,0.0,1.0)
            self.textinput.counter = self.textinput.counter+1
        elif self.textinput.counter==1:
            self.textinput.foreground_color = (0.0,0.5,0.5,1.0)
            self.textinput.counter = self.textinput.counter+1
        elif self.textinput.counter==2:
            self.textinput.foreground_color = (0.0,0.0,1.0,1.0)
            self.textinput.counter = self.textinput.counter+1
        elif self.textinput.counter==3:
            self.textinput.foreground_color = (1.0,0.0,0.5,1.0)
            self.textinput.counter = self.textinput.counter+1
        else:
            self.textinput.foreground_color = (0.0,0.0,0.0,1.0)
            self.textinput.counter=0

        try:
            self.txt_inpt.text = str(int(self.txt_inpt.text)+1)
            self.textinput.text += '\n'+'----------------  '+self.txt_inpt.text+'  ----------------'+'\n'
        except:
            # with open('station_start.txt','rb') as f:
            #    st=str(f.read()).split('\n')[0]
            # f.close()
            st = STATION_START
            self.txt_inpt.text = str(int(st)+1)
            self.textinput.text += '----------------  '+self.txt_inpt.text+'  ----------------'+'\n'

        self.txt_inpt.foreground_color = self.textinput.foreground_color

        #get the last site visited and add 1, write to station file
        # fsite = open('station_start.txt','wb')
        # fsite.write(str(int(self.txt_inpt.text)+1))
        # fsite.close()
        countmax=16; counter=0
        with open('lobos.cfg','rb') as oldfile, open('lobos_new.cfg','wb') as newfile:
           for line in oldfile:
              counter += 1
              if counter==countmax:
                 #newfile.write("            text: '"+st+"'\n")
                 newfile.write('station_start = '+self.txt_inpt.text+'\n')
              else:
                 newfile.write(line)
        mv('lobos_new.cfg','lobos.cfg')

    #=========================
    def station_down(self):
        '''
        decrement station 1
        '''
        try:
            self.txt_inpt.text = str(int(self.txt_inpt.text)-1)
            self.textinput.text += '\n'+'----------------  '+self.txt_inpt.text+'  ----------------'+'\n'
        except:
            # with open('station_start.txt','rb') as f:
            #    st=str(f.read()).split('\n')[0]
            # f.close()
            st = STATION_START
            self.txt_inpt.text = str(int(st)-1)
            self.textinput.text += '----------------  '+self.txt_inpt.text+'  ----------------'+'\n'

        self.txt_inpt.foreground_color = self.textinput.foreground_color

        # # get the last site visited and add 1, write to station file
        # fsite = open('station_start.txt','wb')
        # fsite.write(str(int(self.txt_inpt.text)+1))
        # fsite.close()

        #overwrite the kv file on line 34 with the new station number
        countmax=16; counter=0
        with open('lobos.cfg','rb') as oldfile, open('lobos_new.cfg','wb') as newfile:
           for line in oldfile:
              counter += 1
              if counter==countmax:
                 #newfile.write("            text: '"+st+"'\n")
                 newfile.write('station_start = '+self.txt_inpt.text+'\n')
              else:
                 newfile.write(line)
        mv('lobos_new.cfg','lobos.cfg')

    #=========================
    def SetMode(self, ser2, mode):
        '''
        send camera command to enter 1 of 6 modes
        '''
        if ser2!=0:
            if mode==1:
                self.textinput.text += '** All Off **'+'\n'
                status = ser2.write('00000\r'.encode()) # write command
            elif mode==2:
                self.textinput.text += '** Lights On **'+'\n'
                status = ser2.write('00001\r'.encode()) # write command
            elif mode==3:
                self.textinput.text += '** Lasers On **'+'\n'
                status = ser2.write('00010\r'.encode()) # write command
            elif mode==4:
                self.textinput.text += '** Lights+Lasers On **'+'\n'
                status = ser2.write('00011\r'.encode()) # write command
            elif mode==5:
                self.textinput.text += '** LED/Macro **'+'\n'
                status = ser2.write('01100\r'.encode()) # write command
            elif mode==6:
                self.textinput.text += '***** Macro ReCal *****'+'\n'
                status = ser2.write('10000\r'.encode()) # write command

#=========================
#=========================
class Eyeball_DAQApp(App):

    #=========================
    def __init__(self, **kwargs):
       super(Eyeball_DAQApp, self).__init__(**kwargs)
       self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
       self._keyboard.bind(on_key_down = self._on_keyboard_down)
       self._keyboard.bind(on_key_up = self._on_keyboard_up)

    #=========================
    def _keyboard_closed(self):
       self._keyboard.unbind(on_key_down = self._on_keyboard_down)
       self._keyboard = None

    #=========================
    def _on_keyboard_down(self, *args):
       print args[1][1]

    #=========================
    def _on_keyboard_up(self, *args):
       print args[1][1]

    #=========================
    def _update_time(self, dt):
        self.item.title = 'Time is '+time.asctime()+'. '+'Position is [N: '+str(self.n_txt.text)+', E: '+str(self.e_txt.text)+']'+'\n'

    #=========================
    def _update_pos(self, dt):
        '''
        get and update position
        '''
        e, n, lon, lat = get_nmea(self)

        try:
            self.e_txt.text = e[:10]#self.dat['e'][:10]
            self.n_txt.text = n[:10]#self.dat['n'][:10]
        except:
            pass

        Clipboard.copy(self.n_txt.text+':'+self.e_txt.text)
        tmp = Clipboard.paste()
        self.n_txt.text = tmp.split(':')[0]
        self.e_txt.text = tmp.split(':')[1]

        if MAKEMAP:
            self.map.simple_marker([lat, lon], marker_color='red')
            self.map.save(self.mapname)

        if SHOWMAP:
            # plot position and color code by time elapsed
            secs = time.mktime(time.localtime())-self.starttime
            self.fig.gca().scatter(float(e),float(n),s=30,c=secs, vmin=1, vmax=1200, cmap='Greens')
            self.fig.gca().set_ylim([float(n)-IMBOX_Y, float(n)+IMBOX_Y])
            self.fig.gca().set_xlim([float(e)-IMBOX_X, float(e)+IMBOX_X])
            self.fig.canvas.draw()

    #=========================
    def _update_dep(self, dt):
        '''
        get and update depth
        '''
        d = get_nmeadepth(self)

        self.textinput2.text += d+' m'+'\n'
        if float(d)>10: #self.dat['depth_m']>10:
            self.textinput2.foreground_color = (0.6,0.5,0.0,1.0)
        elif d=='NaN':#self.dat['depth_m']=='NaN':
            self.textinput2.foreground_color = (0.95,0.5,0.25,0.5)
        else:
            self.textinput2.foreground_color = (0.0,0.0,0.0,1.0)

    #=================================================
    # set font sizes for various buttons
    font_size0 = NumericProperty(8)
    font_size = NumericProperty(10)
    font_size1 = NumericProperty(15)
    font_size2 = NumericProperty(20)

    # set up a dummy variable that will get filled by the camera serial port
    ser2 = 99
    fig = 999

    #=========================
    def build(self):
        '''
        build the app
        '''
        #text field for station number
        self.txt_inpt = TextInput(multiline=True)
        self.txt_inpt.text = str(STATION_START) #''

        #text field for easting
        self.e_txt = TextInput(multiline=False)
        self.e_txt.text = ''

        #text field for northing
        self.n_txt = TextInput(multiline=False)
        self.n_txt.text = ''

        #sets the accordion panel for the timestamp
        root = Accordion(orientation='horizontal')
        self.item = AccordionItem(title='Current time is '+time.asctime())

        image = CameraWidget(size_hint = (3.5, 1.0))

        # create data aquisition log
        layout = GridLayout(cols=1)
        self.textinput = Log(text='Data Acquisition Log\n', size_hint = (0.05, .5), markup=True, font_size='10sp')
        self.textinput.counter=0

        # for depth display
        self.textinput2 = Log(text='', size_hint = (0.05, 0.25), markup=True, font_size='35sp')

        # self.fig, self.ax = plt.subplots()
        self.fig = mpl.figure.Figure()

        if MAKEMAP:
            self.map = folium.Map(location=(36.6804,-111.7390), tiles='Stamen Terrain', zoom_start=14, max_zoom=20, min_zoom=0, control_scale=True) #start map around hotnana
            self.mapname = os.path.expanduser("~")+os.sep+time.asctime().replace(' ','_').replace(':','_')+'.html'
            self.map.save(self.mapname)

        if SHOWMAP:
            self = init_fig(self,IMAGEFILE, TFWFILE)

        self.my_mpl_kivy_widget = MatplotFigure(self.fig)


        #add live feed (image) and log window and depth window to gui
        layout.add_widget(self.textinput)
        layout.add_widget(self.my_mpl_kivy_widget)
        layout.add_widget(self.textinput2)

        image.textinput = self.textinput
        image.textinput2 = self.textinput2

        #initiate serial port for gps
        self = init_serial(self,COMNUM) # is the com number this needs to read a config file or something

        #initiate serial port for camera
        self = init_serial2(self,COMNUM2) # is the com number this needs to read a config file or something

        #initiate serial port for echosounder
        self = init_serial3(self,COMNUM3) # is the com number this needs to read a config file or something

        # an object for passing to the mode buttons in the camera widget
        ser2 = self.ser2
        # an object for passing the figure to the camera widget
        fig = self.fig

        # add image to AccordionItem
        self.item.add_widget(image)
        self.item.add_widget(layout)

        #set clock to poll time and posotion on different threads
        Clock.schedule_interval(self._update_time, 1) #update time
        Clock.schedule_interval(self._update_pos, 2) #update position
        Clock.schedule_interval(self._update_dep, 5) #update depth

        root.add_widget(self.item)

        return root

    #=========================
    def on_stop(self):
        '''write session log to file, close ports, etc
        '''
        outfile = os.path.expanduser("~")+os.sep+'log_'+time.asctime().replace(' ','_').replace(':','_')+'.txt'
        with open(outfile,'wb') as f:
           f.write(self.textinput.text)
        f.close()

        # #read the last station number
        # with open('station_start.txt','rb') as f:
        #    st=str(f.read()).split('\n')[0]
        # f.close()

        #overwrite the kv file on line 34 with the new station number
        # countmax=16; counter=0
        # with open('lobos.cfg','rb') as oldfile, open('lobos_new.cfg','wb') as newfile:
        #    for line in oldfile:
        #       counter += 1
        #       if counter==countmax:
        #          #newfile.write("            text: '"+st+"'\n")
        #          newfile.write('station_start = '+self.txt_inpt.text+'\n')
        #       else:
        #          newfile.write(line)
        # mv('lobos_new.cfg','lobos.cfg')


        # #overwrite the kv file on line 34 with the new station number
        # countmax=34; counter=0
        # with open('lobos.kv','rb') as oldfile, open('lobos_new.kv','wb') as newfile:
        #    for line in oldfile:
        #       counter += 1
        #       if counter==countmax:
        #          newfile.write("            text: '"+st+"'\n")
        #       else:
        #          newfile.write(line)
        # mv('lobos_new.kv','lobos.kv')

        # close the serial port for gps
        if self.ser!=0:
           self.ser.close()
           print "================="
           print "GPS is closed"
           print "================="

        # close the serial port for camera
        if self.ser2!=0:
           status = self.ser2.write('00000\r'.encode()) # write command
           self.ser2.close()
           print "================="
           print "serial camera is closed"
           print "================="

        # close the serial port for echosounder
        if self.ser3!=0:
           self.ser3.close()
           print "================="
           print "echosounder is closed"
           print "================="

#=========================
#=========================
if __name__ == '__main__':

    #if they dont exist already, make new folders
    try:
       os.mkdir('eyeballimages')
       os.mkdir('gravelimages')
       os.mkdir('rockimages')
       os.mkdir('sandrockimages')
       os.mkdir('sandgravelimages')
    except:
       pass

    Eyeball_DAQApp().run()

# config = ConfigParser.RawConfigParser()
# config.add_section('lobos')
# config.set('lobos', 'COMNUM', '10') #gps
# config.set('lobos', 'COMNUM2', '4') #camera
# config.set('lobos', 'COMNUM3', '3') #echosounder
# config.set('lobos', 'BAUDRATE', '9600') #GPS
# config.set('lobos', 'BAUDRATE2', '9600') #CAMERA
# config.set('lobos', 'BAUDRATE3', '4800') #ECHOSOUNDER
# config.set('lobos', 'MAKEMAP', 'true')
# config.set('lobos', 'cs2cs_args', "epsg:26949")
#
# # Writing our configuration file
# with open('lobos.cfg', 'wb') as configfile:
#     config.write(configfile)

# #=========================
# def TakePicture(self, fig):#*args):
#     '''takes a sandcam picture and saves it to the eyeball folder
#     '''
#     self.export_to_png = export_to_png
#
#     tmp = Clipboard.paste()
#     self.n_txt.text = tmp.split(':')[0]
#     self.e_txt.text = tmp.split(':')[1]
#
#     now = time.asctime().replace(' ','_').replace(':','_')
#
#     filename = 'st'+self.txt_inpt.text+'_sand_'+now+'_'+self.e_txt.text+'_'+self.n_txt.text+'.png' #
#     self.export_to_png(self.ids.camera, filename=filename)
#
#     subprocess.Popen("python resize_n_move.py -i "+filename+" -o eyeballimages", shell=True)
#     self.textinput.text += 'Eyeball image collected:\n'
#
#     if SHOWMAP:
#         fig.gca().plot(float(self.e_txt.text),float(self.n_txt.text),'ys')
#         fig.canvas.draw()
