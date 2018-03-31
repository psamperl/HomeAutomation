import sys
import linecache
import random
import os
import glob
from ubidots import ApiClient
import math
import time
import ow
import time
import FileLogger
import traceback
import RPi.GPIO as GPIO
from Config import *
from Private import *
import code, traceback, signal
from HWPins import *

# Script collects all temperatures from 1wire sensors.
# It sends it to ubidots

#sudo strace -f -o /tmp/ubidots_strace.log python ubiClient.py

# Create an ApiClient object
api = ApiClient(token=ubidotstoken)
dictTemp = None
collectorpump = '0';
fireplacepump = '0';
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(collecot_pinout, GPIO.OUT)# collector pump
GPIO.setmode(GPIO.BCM)
GPIO.setup(fireplace_pinout, GPIO.OUT)# fireplace pump

class Timeout():
  """Timeout class using ALARM signal"""
  class Timeout(Exception): pass

  def __init__(self, sec):
    self.sec = sec

  def __enter__(self):
    signal.signal(signal.SIGALRM, self.raise_timeout)
    signal.alarm(self.sec)

  def __exit__(self, *args):
    signal.alarm(0) # disable alarm

  def raise_timeout(self, *args):
    raise Timeout.Timeout()

def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
            os._exit(1)

    except KeyboardInterrupt:
        print("Ok ok, quitting")
        os._exit(1)

    # restore the exit gracefully handler here    
    signal.signal(signal.SIGINT, exit_gracefully)
	
def traceit(frame, event, arg):
    if event == "line":
        lineno = frame.f_lineno
        filename = frame.f_globals["__file__"]
        print "file %s line %d" % (filename, lineno)
    return traceit

def init():
	try:
		ow.init('localhost:4304')
		return True
	except:
		print (time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc())

		if logger:
			logger.error((time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc()), exc_info=True)
			return False

#read all temperatures
def read_all_temp():
	#create dictionary
	sensorDict = {}
	try:
		sensors = ow.Sensor("/").sensorList()

		#ignore sensors which are not DS18B20
		for sensor in sensors[:]:
			if sensor.type != 'DS18B20':
					sensors.remove( sensor )

		#Fill dictionary
		for sensor in sensors:
			if sensor.r_address in sDict:
				#Sensor has name defined
				sensorDict[sDict[sensor.r_address]] = "%.2f" % float(sensor.temperature)
			else:
				#Sensor name missing. Creating new one
				sensorDict['T_' + sensor.r_address] = "%.2f" % float(sensor.temperature)
	except:
		print (time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc())

		if logger:
			logger.error((time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc()), exc_info=True)
		return -1;
	return sensorDict

#sys.settrace(traceit)

print "Starting temperature agregator for Ubidots..."

# Start File Logger
print "Starting Logger.."
global logger
logger = FileLogger.startLogger("/var/log/ubidots.log", 1000000, 5)
logger.info("Starting Logger...")

# store the original SIGINT handler
original_sigint = signal.getsignal(signal.SIGINT)
signal.signal(signal.SIGINT, exit_gracefully)

# Initialize RPi_Temp module
if not init():
	print "Error: initializing RPi_Temp"
	sys.exit()

while(1):
    try:
    	#read temperatures from owfs
		logger.info("Read temperatures...")
		dictTemp = read_all_temp()
		if (GPIO.input(collecot_pinout) == True): # Physically read the pin now
			collectorpump = '0'
		else:
			collectorpump = '1'
			
		if (GPIO.input(fireplace_pinout) == True): # Physically read the pin now
			fireplacepump = '0'
		else:
			fireplacepump = '1'
			
			
		if(dictTemp != -1):
			#print dictTemp
			if (dictTemp != None):
				logger.info(time.strftime("[%H:%M:%S]: ", time.localtime()) +  'Tbojler:' + dictTemp['Tbojler'] + ' Tsanitarna:' + dictTemp['Tsanitarna']+' Trkam:' + dictTemp['Trkam']+' Toutside:' + dictTemp['Toutside']+' Tinside:' + dictTemp['Tinside']+' Tcollector:' + dictTemp['Tcollector'] +' Pcollector:' + collectorpump)
				print(time.strftime("[%H:%M:%S]: ", time.localtime()) +  'Tbojler:' + dictTemp['Tbojler'] + ' Tsanitarna:' + dictTemp['Tsanitarna']+' Trkam:' + dictTemp['Trkam']+' Toutside:' + dictTemp['Toutside']+' Tinside:' + dictTemp['Tinside']+' Tcollector:' + dictTemp['Tcollector'] +' Pcollector:' + collectorpump)
				try:
					with Timeout(60):
						#ubidots does not support tags or names so id is the only thing we can send at the moment
						api.save_collection([
						  {'variable': '5884c724762542630e9a87d0', 'value': dictTemp['Tbojler']}, 
						  {'variable': '5884c755762542630e9a892e', 'value': dictTemp['Tsanitarna']},
						  {'variable': '5884c768762542630faa1614', 'value': dictTemp['Trkam']},
						  {'variable': '5884cf71762542630da216e1', 'value': dictTemp['Toutside']},
						  {'variable': '5884cf68762542631035b438', 'value': dictTemp['Tinside']},
						  {'variable': '5884cf7f7625426311a70cb9', 'value': dictTemp['Tcollector']},
						  {'variable': '58a17d667625422f401fe4ea', 'value': dictTemp['Tfireplace']},
						  {'variable': '588529757625422b13a272d3', 'value': collectorpump},
						  {'variable': '58a1a0b07625422f40214093', 'value': fireplacepump}
						])
						  #{'variable': '588529757625422b13a272d3', 'value': collectorpump}
							
						logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Send OK')
						print(time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Send OK')
				except Timeout.Timeout:
					if logger: logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Timeout on plot")
				except:	
					print (time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc())
					if logger:
						logger.error((time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc()), exc_info=True)
		else:
			logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'dictTemp missing!')
		time.sleep(60)
    except:	
    	print (time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc())
        if logger:
        	logger.error((time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc()), exc_info=True)
			
			
			
