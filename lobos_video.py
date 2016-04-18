"""
lobos_video.py
program to
1) view and capture a video
2) capture gps andf depths
3) write video file

Written by:
Daniel Buscombe, April 2016
Grand Canyon Monitoring and Research Center, U.G. Geological Survey, Flagstaff, AZ
please contact:
dbuscombe@usgs.gov

SYNTAX:
python lobos_video.py

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
import serial
from pynmea import nmea
import pyproj
import ConfigParser

import random, string

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

# video frames per second
FPS = int(config.get('lobos', 'fps'))

#============= END config =====================================

# =========================================================
def id_generator(size=6, chars=string.ascii_uppercase ): #+ string.digits
   return ''.join(random.choice(chars) for _ in range(size))

#=========================
def init_serial3(self,portnum):
    '''initialise serial port for echosounder
    '''
    comnum = 'COM' + str(portnum)

    # now = time.asctime().replace(' ','_').replace(':','_')
    try:
        global BAUDRATE3
        self.ser3 = serial.Serial()
        self.ser3.baudrate = BAUDRATE3
        self.ser3.port = comnum
        self.ser3.timeout = 0.5
        self.ser3.open()
        if self.ser3.isOpen():
            # self.textinput.text += 'Echosounder opened on port '+str(portnum)+'\n'
            print '==========================='
            print 'Echosounder is open'
            print '==========================='
            self.echosounderopen = 1
    except:
        # self.textinput.text += 'Echosounder failed to open on port '+str(portnum)+'\n'
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

 # now = time.asctime().replace(' ','_').replace(':','_')
 try:
     global BAUDRATE2
     self.ser2 = serial.Serial()
     self.ser2.baudrate = BAUDRATE2
     self.ser2.port = comnum
     self.ser2.timeout = 0.5
     self.ser2.open()
     if self.ser2.isOpen():
        # self.textinput.text += 'Camera serial opened on port '+str(portnum)+'\n'
        print '==========================='
        print 'Camera serial is open'
        print '==========================='
        self.camopen = 1
 except:
    #  self.textinput.text += 'Camera serial failed to open on port '+str(portnum)+'\n'
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
        # self.textinput.text += 'GPS opened on port '+str(portnum)+'\n'
        print '==========================='
        print 'GPS is open'
        print '==========================='
        self.gpsopen = 1
 except:
    #  self.textinput.text += 'GPS failed to open on port '+str(portnum)+'\n'
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

    while (gotpos==0) &(counter<2):
       line = self.ser.read(500) # read 1000 bytes
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
       depth_ft = self.ser3.read(100).split('DBT')[1].split(',f,')[0].split(',')[1]
       d = str(float(depth_ft)*0.3048)
    except:
       d = 'NaN'

    return d

#=========================
#=========================
## kv markup for building the app
Builder.load_file('lobos_video.kv')

#=========================
#=========================
class CameraWidget(BoxLayout):
    '''
    class that defines the camera widget
    and interacts with the buttons in the app (takes images, sets modes, etc)
    '''
    number = NumericProperty()
    tag = StringProperty()
    def __init__(self, **kwargs):
        super(CameraWidget, self).__init__(**kwargs)
        Clock.schedule_interval(self.increment_time, 1/FPS)
        #self.increment_time(0)
        self.tag = id_generator()

    #=========================
    def increment_time(self, interval):

        self.number += 1
        if self.number<10:
            #export_to_png(self.ids.camera, filename=os.path.normpath(os.path.join(os.getcwd(),'videos',self.tag+'im0'+str(self.number)+'.png')))
            Window.screenshot(name=os.path.normpath(os.path.join(os.getcwd(),'videos','im0'+str(self.number)+'_'+self.tag+'.png')))
        else:
            #export_to_png(self.ids.camera, filename=os.path.normpath(os.path.join(os.getcwd(),'videos',self.tag+'im'+str(self.number)+'.png')))
            Window.screenshot(name=os.path.normpath(os.path.join(os.getcwd(),'videos','im'+str(self.number)+'_'+self.tag+'.png')))

    #=========================
    def start(self):
        self.ids['start'].background_color = 1.0, 0.0, 0.0, 1.0
        self.tag = id_generator() #give a set of images unique ids

        Clock.unschedule(self.increment_time)
        Clock.schedule_interval(self.increment_time, 1/FPS)

    #=========================
    def stop(self):
        self.ids['start'].background_color = 0.75, 0.75, 0.75, 1.0
        Clock.unschedule(self.increment_time)
        subprocess.Popen("python compile_movie.py -i "+str(FPS)+" -t "+self.tag, shell=True)

    #=========================
    def SetMode(self, ser2, mode):
        '''
        send camera command to enter 1 of 6 modes
        '''
        if ser2!=0:
            if mode==1:
                status = ser2.write('00000\r'.encode()) # write command
            elif mode==2:
                status = ser2.write('00001\r'.encode()) # write command
            elif mode==3:
                status = ser2.write('00010\r'.encode()) # write command
            elif mode==4:
                status = ser2.write('00011\r'.encode()) # write command
            elif mode==5:
                status = ser2.write('01100\r'.encode()) # write command
            elif mode==6:
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
        self.item.title = time.asctime()+'/[N: '+str(self.n_txt.text)+', E: '+str(self.e_txt.text)+']/[D: '+str(self.d_txt.text)+']'+'\n'

    #=========================
    def _update_pos(self, dt):
        '''
        get and update position
        '''
        e, n, lon, lat = get_nmea(self)
        d = get_nmeadepth(self)
        try:
            self.e_txt.text = e[:10]#self.dat['e'][:10]
            self.n_txt.text = n[:10]#self.dat['n'][:10]
            self.d_txt.text = d
        except:
            pass

        Clipboard.copy(self.n_txt.text+':'+self.e_txt.text+':'+self.d_txt.text)

    # #=========================
    # def _update_dep(self, dt):
    #     '''
    #     get and update depth
    #     '''
    #     d = get_nmeadepth(self)

    #=================================================
    # set font sizes for various buttons
    font_size0 = NumericProperty(8)
    font_size = NumericProperty(10)
    font_size1 = NumericProperty(15)
    font_size2 = NumericProperty(20)

    # set up a dummy variable that will get filled by the camera serial port
    ser2 = 99

    #=========================
    def build(self):
        '''
        build the app
        '''

        #text field for easting
        self.e_txt = TextInput(multiline=False)
        self.e_txt.text = ''

        #text field for northing
        self.n_txt = TextInput(multiline=False)
        self.n_txt.text = ''

        #text field for depth
        self.d_txt = TextInput(multiline=False)
        self.d_txt.text = ''

        #sets the accordion panel for the timestamp
        root = Accordion(orientation='vertical')#'horizontal')
        self.item = AccordionItem(title='Current time is '+time.asctime())

        image = CameraWidget(size_hint = (3.5, 1.0))

        #initiate serial port for gps
        self = init_serial(self,COMNUM) # is the com number this needs to read a config file or something

        #initiate serial port for camera
        self = init_serial2(self,COMNUM2) # is the com number this needs to read a config file or something

        #initiate serial port for echosounder
        self = init_serial3(self,COMNUM3) # is the com number this needs to read a config file or something

        # an object for passing to the mode buttons in the camera widget
        ser2 = self.ser2

        # add image to AccordionItem
        self.item.add_widget(image)

        #set clock to poll time and posotion on different threads
        Clock.schedule_interval(self._update_time, 1) #update time
        Clock.schedule_interval(self._update_pos, 4) #update position
        #Clock.schedule_interval(self._update_dep, 5) #update depth

        root.add_widget(self.item)

        return root

    #=========================
    def on_stop(self):
        '''write session log to file, close ports, etc
        '''
        # close the serial port for gps
        if self.ser!=0:
           self.ser.close()
           print "================="
           print "GPS is closed"
           print "================="

        # close the serial port for camera
        if self.ser2!=0:
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
       os.mkdir('videos')
    except:
       pass

    Eyeball_DAQApp().run()

# def export_to_png(self, filename, *args):
#     '''Saves an image of the widget and its children in png format at the
#     specified filename. Works by removing the widget canvas from its
#     parent, rendering to an :class:`~kivy.graphics.fbo.Fbo`, and calling
#     :meth:`~kivy.graphics.texture.Texture.save`.
#     '''
#
#     if self.parent is not None:
#         canvas_parent_index = self.parent.canvas.indexof(self.canvas)
#         self.parent.canvas.remove(self.canvas)
#
#     fbo = Fbo(size=self.size,  with_stencilbuffer=True)
#
#     with fbo:
#         ClearColor(0, 0, 0, 1)
#         ClearBuffers()
#         Translate(-self.x, -self.y, 0)
#
#     fbo.add(self.canvas)
#     fbo.draw()
#     fbo.texture.save(filename, flipped=False)
#     fbo.remove(self.canvas)
#
#     if self.parent is not None:
#         self.parent.canvas.insert(canvas_parent_index, self.canvas)
#
#     return True


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

        # create data aquisition log
        #layout = GridLayout(cols=1)
        #self.textinput = Log(text='Data Acquisition Log\n', size_hint = (0.05, .7), markup=True, font_size='10sp')
        #self.textinput.counter=0

        # for depth display
        #self.textinput2 = Log(text='', size_hint = (0.05, 0.1), markup=True, font_size='25sp')

        #add live feed (image) and log window and depth window to gui
        #layout.add_widget(self.textinput)
        #layout.add_widget(self.textinput2)

        #image.textinput = self.textinput
        #image.textinput2 = self.textinput2

        # outfile = os.path.expanduser("~")+os.sep+'log_'+time.asctime().replace(' ','_').replace(':','_')+'.txt'
        # with open(outfile,'wb') as f:
        #    f.write(self.textinput.text)
        # f.close()
