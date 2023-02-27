#!/usr/bin/env python

import RPi.GPIO as GPIO
import time
import ow
import FileLogger
from Config import *
from HWPins import *

# Script acts as a differential thermostat.
# It switches on fireplace pump in case temperature in fireplace higher than 8

#calculate hyst
def hyst(x, th_lo, th_hi, initial = False):
    hi = x >= th_hi
    lo_or_hi = (x <= th_lo) | hi
    ind = np.nonzero(lo_or_hi)[0]
    if not ind.size: # prevent index error if ind is empty
        return np.zeros_like(x, dtype=bool) | initial
    cnt = np.cumsum(lo_or_hi) # from 0 to len(x)
    return np.where(cnt, hi[ind[cnt-1]], initial)


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


        except Exception, e:
        	print (time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc())
		logger.info (time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc())
		return -1;


        return sensorDict


# Start File Logger
print "Starting Logger.." 
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(fireplace_pinout, GPIO.OUT)
GPIO.output(fireplace_pinout,True) #Turn power OFF

global logger
logger = FileLogger.startLogger("/var/log/fireplace.log", 1000000, 5) 
state = True 
dictTemp = None
logger.info("Starting Logger...")

ow.init('localhost:4304')

"""i = 0
Sanitarna = 60
Tfireplace = 30
"""
# endless loop, on/off for 1 second
while True:

	try:
		dictTemp = read_all_temp()
		if(dictTemp != -1):

			if(float(dictTemp['Tfireplace']) > 60):
				print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Tfireplace > 60 Pumpa ON')
				state = True
	        	elif(float(dictTemp['Tbojler']) <= float(dictTemp['Tfireplace']) - 8):
				print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Tsanitarna <= Tfireplace-8 Pumpa ON')
				state = True
			elif(float(dictTemp['Tbojler']) > float(dictTemp['Tfireplace']) - 2):
				print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Tsanitarna > Tfireplace-2 Pumpa OFF')
				state = False


			if(state == False):
				logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Pumpa OFF')
				GPIO.output(fireplace_pinout,True) #Turn power OFF
			else:
				logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Pumpa ON')
				GPIO.output(fireplace_pinout,False) #Turn power ON

			logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Tfire ' + dictTemp['Tfireplace'] + "\t" + 'Tbojler ' + dictTemp['Tbojler'] + "\t" + 'Pump=' + str(state))
			print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Tfireplace ' + dictTemp['Tfireplace'] + "\t" + 'Tbojler ' + dictTemp['Tbojler'] + "\t" + 'Kamin pumpa ' + str(state))
		else:
			logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'dictTemp missing')
		time.sleep(10)
	except Exception, e:
		logger.info("Exception durring runtime")
        	print (time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc())
		logger.info (time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc())



