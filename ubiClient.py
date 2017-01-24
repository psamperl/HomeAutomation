import sys
import os
import glob
from ubidots import ApiClient
import math
import time
import MySQLdatabase
import ow
import time
import FileLogger
import traceback
import RPi.GPIO as GPIO
from Config import *
from Private import *

# Create an ApiClient object
api = ApiClient(token=ubidotstoken)
dictTemp = None
collectorpump = 0;
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN)

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



print "Starting temperature agregator for Ubidots..."

# Start File Logger
print "Starting Logger.."
global logger
logger = FileLogger.startLogger("/var/log/ubidots.log", 1000000, 5)
logger.info("Starting Logger...")

# Initialize RPi_Temp module
if not init():
	print "Error: initializing RPi_Temp"
	sys.exit()

while(1):
    try:
    	#read temperatures from owfs
		logger.info("Read temperatures...")
		dictTemp = read_all_temp()
		if (GPIO.input(27) == True): # Physically read the pin now
			collectorpump = '0'
		else:
			collectorpump = '1'
		if(dictTemp != -1):
			#print dictTemp
			if (dictTemp != None):
				logger.info(time.strftime("[%H:%M:%S]: ", time.localtime()) +  'Tbojler:' + dictTemp['Tbojler'] + ' Tsanitarna:' + dictTemp['Tsanitarna']+' Tkamin:' + dictTemp['Tkamin']+' Toutside:' + dictTemp['Toutside']+' Tinside:' + dictTemp['Tinside']+' Tcollector:' + dictTemp['Tcollector']+' Pcollector:' + collectorpump)
				print(time.strftime("[%H:%M:%S]: ", time.localtime()) +  'Tbojler:' + dictTemp['Tbojler'] + ' Tsanitarna:' + dictTemp['Tsanitarna']+' Tkamin:' + dictTemp['Tkamin']+' Toutside:' + dictTemp['Toutside']+' Tinside:' + dictTemp['Tinside']+' Tcollector:' + dictTemp['Tcollector']+' Pcollector:' + collectorpump)
				try:
					api.save_collection([
					  {'variable': '5884c724762542630e9a87d0', 'value': dictTemp['Tbojler']}, 
					  {'variable': '5884c755762542630e9a892e', 'value': dictTemp['Tsanitarna']},
					  {'variable': '5884c768762542630faa1614', 'value': dictTemp['Tkamin']},
					  {'variable': '5884cf71762542630da216e1', 'value': dictTemp['Toutside']},
					  {'variable': '5884cf68762542631035b438', 'value': dictTemp['Tinside']},
					  {'variable': '5884cf7f7625426311a70cb9', 'value': dictTemp['Tcollector']},
					  {'variable': '588529757625422b13a272d3', 'value': collectorpump}
					])	
					logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Send OK')
					print(time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Send OK')
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
