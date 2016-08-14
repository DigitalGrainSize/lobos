
## Daniel Buscombe, August 2016

#================================================
COMNUM=4
BAUDRATE = 38000
cs2cs_args = 'epsg:26949'
# ===============================================

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.accordion import *
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import *
from kivy.graphics import Canvas, Translate, Fbo, ClearColor, ClearBuffers
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
from kivy.uix.textinput import TextInput

import subprocess
import serial
from pynmea import nmea
import pyproj
import time, os

# get the transformation matrix of desired output coordinates
try:
   trans =  pyproj.Proj(init=cs2cs_args)
except:
   trans =  pyproj.Proj(cs2cs_args)


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
        print '==========================='
        print 'GPS is open'
        print '==========================='
        self.gpsopen = 1
 except:
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
       line = self.ser.read(500) # read 400 bytes
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
            long = 0
            lat = 0

    return str(e), str(n), -long, lat

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
    
#===========================================================================================
#============================================================================================
# start app

#=========================
## kv markup for building the app
Builder.load_file('polecam_play.kv')

#=========================
#=========================
class CameraWidget(BoxLayout):
    #=========================
    def TakePicture(self):
        '''takes a picture and saves it to the folder
        '''
        self.export_to_png = export_to_png

        tmp = Clipboard.paste()
        n_txt = tmp.split(':')[0]
        e_txt = tmp.split(':')[1]

        now = time.asctime().replace(' ','_').replace(':','_')

        filename = 'im_'+now+'_'+e_txt+'_'+n_txt+'.png'
        #filename = 'im_'+now+'.png'

        self.export_to_png(self.ids.camera, filename=filename)

        subprocess.Popen("python move_polecam_im.py -i "+filename+" -o GPSCam_images", shell=True)

#=========================
#=========================
class GPSCam(App):

    font_size8 = NumericProperty(8)
    font_size20 = NumericProperty(20)

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

        #sets the accordion panel for the timestamp
        root = Accordion(orientation='horizontal')
        self.item = AccordionItem(title='Current time is '+time.asctime())

        image = CameraWidget(size_hint = (3.5, 1.0))

        #initiate serial port for gps
        self = init_serial(self,COMNUM) # is the com number this needs to read a config file or something

        # add image to AccordionItem
        self.item.add_widget(image)

        #set clock to poll time and posotion on different threads
        Clock.schedule_interval(self._update_time, 1) #update time
        Clock.schedule_interval(self._update_pos, 1) #1.6) #update position

        root.add_widget(self.item)

        return root


    #=========================
    def on_stop(self):
        '''close ports, etc
        '''
        
        # close the serial port for gps
        if self.ser!=0:
           self.ser.close()
           print "================="
           print "GPS is closed"
           print "================="


# ==============================================================================
# ============ run app =========================================================
#==============================================================================

#=========================
#=========================
if __name__ == '__main__':

    try:
       os.mkdir('GPSCam_images')
    except:
       pass


    GPSCam().run() 