"""
lobos_v2.py
program to
1) view and capture an image of sediment
2) get site info from the user
3) save image to file with the site and time in the file name

Written by:
Daniel Buscombe, Feb-March 2015, updated June 2015, December 2015, April 2016
Grand Canyon Monitoring and Research Center, U.G. Geological Survey, Flagstaff, AZ
please contact:
dbuscombe@usgs.gov

SYNTAX:
python lobos_v2.py

REQUIREMENTS:
python
kivy (http://kivy.org/#home)
pyserial
pynmea
pyproj
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
import random

# com-number for serial port gps
COMNUM = 10

# com-number for serial port camera
COMNUM2 = 4

# com-number for echosounder
COMNUM3 = 2

#same baud rate for gps
BAUDRATE = 9600

#set baud rate for caemra
BAUDRATE2 = 9600

#baud rate for echosounder
BAUDRATE3 = 4800

# log eastings and northings in arizona state plane central
cs2cs_args = "epsg:26949"
# get the transformation matrix of desired output coordinates
try:
   trans =  pyproj.Proj(init=cs2cs_args)
except:
   trans =  pyproj.Proj(cs2cs_args)

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

 #self.ids.mode1.ser = self.ser2

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

    while (gotpos==0) &(counter<3):
       line = self.ser.read(1000) # read 1000 bytes
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
    #dat = {}

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
        #dat['e'] = str(e)
        #dat['n'] = str(n)
        #dat['alt'] = str(gpgga.antenna_altitude)
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
            #dat['e'] = str(e); dat['n'] = str(n)

        except:
            pass

    try:
       depth_ft = self.ser3.read(100).split('DBT')[1].split(',f,')[0].split(',')[1]
       d = str(float(depth_ft)*0.3048)
    except:
       #dat['depth_ft'] = 'NaN'
       #dat['depth_m'] = 'NaN'
       d = 'NaN'

    return str(e), str(n), d #dat

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
    def TakePicture(self, *args):
        '''takes a sandcam picture and saves it to the eyeball folder
        '''
        self.export_to_png = export_to_png

        tmp = Clipboard.paste()
        self.n_txt.text = tmp.split(':')[0]
        self.e_txt.text = tmp.split(':')[1]

        now = time.asctime().replace(' ','_').replace(':','_')

        filename = 'st'+self.txt_inpt.text+'_sand_'+now+'_'+self.e_txt.text+'_'+self.n_txt.text+'.png' #
        self.export_to_png(self.ids.camera, filename=filename)

        subprocess.Popen("python resize_n_move.py -i "+filename+" -o eyeballimages", shell=True)
        #subprocess.Popen("python resize_n_move.py -i "+os.path.normpath(os.path.join(os.gwtcwd(),filename))+" -o eyeballimages", shell=True)
        self.textinput.text += 'Eyeball image collected:\n'#+ filename.split('.png')[0]+'\n' #: '+filename+'\n'

    #=========================
    def TakePictureMud(self, *args):
        '''takes a mud picture
        '''
        self.export_to_png = export_to_png

        tmp = Clipboard.paste()
        self.n_txt.text = tmp.split(':')[0]
        self.e_txt.text = tmp.split(':')[1]

        now = time.asctime().replace(' ','_').replace(':','_')

        filename = 'st'+self.txt_inpt.text+'_mud_'+now+'.png'
        self.export_to_png(self.ids.camera, filename=filename)

        subprocess.Popen("python resize_n_move.py -i "+filename+" -o mudimages", shell=True)

        self.textinput.text += 'Mud image collected:\n'#+ filename.split('.png')[0]+'\n' #: '+filename+'\n'

    #=========================
    def TakePictureGravel(self, *args):
        '''takes a gravel picture
        '''
        self.export_to_png = export_to_png

        tmp = Clipboard.paste()
        self.n_txt.text = tmp.split(':')[0]
        self.e_txt.text = tmp.split(':')[1]

        now = time.asctime().replace(' ','_').replace(':','_')

        filename = 'st'+self.txt_inpt.text+'_gravel_'+now+'.png'
        self.export_to_png(self.ids.camera, filename=filename)

        subprocess.Popen("python resize_n_move.py -i "+filename+" -o gravelimages", shell=True)

        self.textinput.text += 'Gravel image collected:\n'#+ filename.split('.png')[0]+'\n' #: '+filename+'\n'

    #=========================
    def TakePictureRock(self, *args):
        '''takes a picture or rocks
        '''
        self.export_to_png = export_to_png

        tmp = Clipboard.paste()
        self.n_txt.text = tmp.split(':')[0]
        self.e_txt.text = tmp.split(':')[1]

        now = time.asctime().replace(' ','_').replace(':','_')

        filename = 'st'+self.txt_inpt.text+'_rock_'+now+'.png'
        self.export_to_png(self.ids.camera, filename=filename)

        subprocess.Popen("python resize_n_move.py -i "+filename+" -o rockimages", shell=True)

        self.textinput.text += 'Rock image collected:\n'#+ filename.split('.png')[0]+'\n' #: '+filename+'\n'

    #=========================
    def TakePictureSandRock(self, *args):
        '''takes a picture of sand and rocks
        '''
        self.export_to_png = export_to_png

        tmp = Clipboard.paste()
        self.n_txt.text = tmp.split(':')[0]
        self.e_txt.text = tmp.split(':')[1]

        now = time.asctime().replace(' ','_').replace(':','_')

        filename = 'st'+self.txt_inpt.text+'_sandrock_'+now+'.png'
        self.export_to_png(self.ids.camera, filename=filename)

        subprocess.Popen("python resize_n_move.py -i "+filename+" -o sandrockimages", shell=True)

        self.textinput.text += 'Sand/Rock image collected:\n'#+ filename.split('.png')[0]+'\n' #: '+filename+'\n'

    #=========================
    def TakePictureSandGravel(self, *args):
        '''takes a picture of sand and gravel
        '''
        self.export_to_png = export_to_png

        tmp = Clipboard.paste()
        self.n_txt.text = tmp.split(':')[0]
        self.e_txt.text = tmp.split(':')[1]

        now = time.asctime().replace(' ','_').replace(':','_')

        filename = 'st'+self.txt_inpt.text+'_sandgravel_'+now+'.png'
        self.export_to_png(self.ids.camera, filename=filename)

        subprocess.Popen("python resize_n_move.py -i "+filename+" -o sandgravelimages", shell=True)

        self.textinput.text += 'Sand/Gravel image collected:\n'#+ filename.split('.png')[0]+'\n' #: '+filename+'\n'

    #=========================
    def TakePictureGravelSand(self, *args):
        '''
        take picture of gravel and sand
        '''
        self.export_to_png = export_to_png

        tmp = Clipboard.paste()
        self.n_txt.text = tmp.split(':')[0]
        self.e_txt.text = tmp.split(':')[1]

        now = time.asctime().replace(' ','_').replace(':','_')

        filename = 'st'+self.txt_inpt.text+'_gravelsand_'+now+'.png'
        self.export_to_png(self.ids.camera, filename=filename)

        subprocess.Popen("python resize_n_move.py -i "+filename+" -o gravelsandimages", shell=True)

        self.textinput.text += 'Gravel/sand image collected:\n'#+ filename.split('.png')[0]+'\n' #: '+filename+'\n'

    #=========================
    def change_st(self):
        '''
        changes station and prints to log
        '''
        self.textinput.text += 'Station is '+self.txt_inpt.text+'\n'

        # get the last site visited and add 1, write to station file
        fsite = open('station_start.txt','wb')
        fsite.write(str(int(self.txt_inpt.text)+1))
        fsite.close()

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
            self.textinput.text += 'Station is '+self.txt_inpt.text+'\n'
        except:
            with open('station_start.txt','rb') as f:
               st=str(f.read()).split('\n')[0]
            f.close()
            self.txt_inpt.text = str(int(st)+1)
            self.textinput.text += 'Station is '+self.txt_inpt.text+'\n'

        self.txt_inpt.foreground_color = self.textinput.foreground_color

        # get the last site visited and add 1, write to station file
        fsite = open('station_start.txt','wb')
        fsite.write(str(int(self.txt_inpt.text)+1))
        fsite.close()

    #=========================
    def station_down(self):
        '''
        decrement station 1
        '''
        try:
            self.txt_inpt.text = str(int(self.txt_inpt.text)-1)
            self.textinput.text += 'Station is '+self.txt_inpt.text+'\n'
        except:
            with open('station_start.txt','rb') as f:
               st=str(f.read()).split('\n')[0]
            f.close()
            self.txt_inpt.text = str(int(st)-1)
            self.textinput.text += 'Station is '+self.txt_inpt.text+'\n'

        self.txt_inpt.foreground_color = self.textinput.foreground_color

        # get the last site visited and add 1, write to station file
        fsite = open('station_start.txt','wb')
        fsite.write(str(int(self.txt_inpt.text)+1))
        fsite.close()

    #=========================
    def Mode1(self, ser2):
        '''
        send camera command to enter mode 1 (lights and lasers off)
        mid water column focus
        '''
        self.textinput.text += 'All off / MWF @ '+time.asctime()+'\n'
        if ser2!=0:
           status = ser2.write('00000\r'.encode()) # write command

    #=========================
    def Mode2(self, ser2):
        '''
        send camera command to enter mode 2 (lights on and lasers off)
        mid water column focus
        '''
        self.textinput.text += 'Lights on / MWF @ '+time.asctime()+'\n'
        if ser2!=0:
            status = ser2.write('00001\r'.encode()) # write command

    #=========================
    def Mode3(self, ser2):
        '''
        send camera command to enter mode 3 (lights off and lasers on)
        mid water column focus
        '''
        self.textinput.text += 'Lasers on / MWF @ '+time.asctime()+'\n'
        if ser2!=0:
            status = ser2.write('00010\r'.encode()) # write command

    #=========================
    def Mode4(self, ser2):
        '''
        send camera command to enter mode 4 (lights and lasers on)
        mid water column focus
        '''
        self.textinput.text += 'Lights + Lasers on / MWF @ '+time.asctime()+'\n'
        if ser2!=0:
            status = ser2.write('00011\r'.encode()) # write command

    #=========================
    def Mode5(self, ser2):
        '''
        send camera command to enter mode 5 (lights and lasers off, LEDS on)
        macro focus
        '''
        self.textinput.text += 'LED / Macro @ '+time.asctime()+'\n'
        if ser2!=0:
            status = ser2.write('01100\r'.encode()) # write command

    #=========================
    def Mode6(self, ser2):
        '''
        send camera command to enter mode 6
        run macro focus recalibration routine
        '''
        self.textinput.text += 'Macro-focus recalibration @ '+time.asctime()+'\n'
        if ser2!=0:
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
        #self.item.title = 'Current time is '+time.asctime()
        self.item.title = 'Time is '+time.asctime()+'. '+'Position is [N: '+str(self.n_txt.text)+', E: '+str(self.e_txt.text)+']'+'\n'

    #=========================
    def _update_pos(self, dt):
        '''
        get and update position
        '''
        #self.dat = get_nmea(self)
        e, n, d = get_nmea(self)
        #now = time.asctime().replace(' ','_').replace(':','_')
        try:
            self.e_txt.text = e[:10]#self.dat['e'][:10]
            self.n_txt.text = n[:10]#self.dat['n'][:10]
        except:
            pass
        #self.textinput.text += 'Position obtained: '+now+'\n'

        Clipboard.copy(self.n_txt.text+':'+self.e_txt.text)
        tmp = Clipboard.paste()
        self.n_txt.text = tmp.split(':')[0]
        self.e_txt.text = tmp.split(':')[1]

        #self.textinput.text += 'N: '+str(self.n_txt.text)+', E: '+str(self.e_txt.text)+', D: '+str(self.dat['depth_m'])+'\n'

        #self.textinput2.text += str(self.dat['depth_m'])+' m'+'\n'
        self.textinput2.text += d+' m'+'\n'
        if float(d)>10: #self.dat['depth_m']>10:
            self.textinput2.foreground_color = (0.6,0.5,0.0,1.0)
        elif d=='NaN':#self.dat['depth_m']=='NaN':
            self.textinput2.foreground_color = (0.25,0.5,0.25,0.25)
        else:
            self.textinput2.foreground_color = (0.0,0.0,0.0,0.0)

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
        #text field for station number
        self.txt_inpt = TextInput(multiline=True)
        self.txt_inpt.text = ''

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
        self.textinput2 = Log(text='', size_hint = (0.05, 0.05), markup=True, font_size='20sp')

        #add live feed (image) and log window and depth window to gui
        layout.add_widget(self.textinput)
        layout.add_widget(self.textinput2)

        image.textinput = self.textinput
        image.textinput2 = self.textinput2

        #initiate serial port for gps
        self = init_serial(self,COMNUM) #0 is the com number this needs to read a config file or something

        #initiate serial port for camera
        self = init_serial2(self,COMNUM2) #0 is the com number this needs to read a config file or something

        #initiate serial port for echosounder
        self = init_serial3(self,COMNUM3) #0 is the com number this needs to read a config file or something

        # an object for passing to the mode buttons in the camera widget
        ser2 = self.ser2

        # add image to AccordionItem
        self.item.add_widget(image)
        self.item.add_widget(layout)

        #set clock to poll time and posotion on different threads
        Clock.schedule_interval(self._update_time, 1) #update time
        Clock.schedule_interval(self._update_pos, 4) #update position

        root.add_widget(self.item)

        return root

    #=========================
    def on_stop(self):
        '''write session log to file, close ports, etc
        '''
        with open(os.path.expanduser("~")+os.sep+'log_'+time.asctime().replace(' ','_').replace(':','_')+'.txt','wb') as f:
           f.write(self.textinput.text)
        f.close()

        #read the last station number
        with open('station_start.txt','rb') as f:
           st=str(f.read()).split('\n')[0]
        f.close()

        #overwrite the kv file on line 34 with the new station number
        countmax=34; counter=0
        with open('lobos.kv','rb') as oldfile, open('lobos_new.kv','wb') as newfile:
           for line in oldfile:
              counter += 1
              if counter==countmax:
                 newfile.write("            text: '"+st+"'\n")
              else:
                 newfile.write(line)
        mv('lobos_new.kv','lobos.kv')

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
       os.mkdir('eyeballimages')
       os.mkdir('gravelimages')
       os.mkdir('rockimages')
       os.mkdir('sandrockimages')
       os.mkdir('sandgravelimages')
    except:
       pass

    Eyeball_DAQApp().run()
