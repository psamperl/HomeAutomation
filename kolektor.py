#!/usr/bin/env python

import RPi.GPIO as GPIO
import time
import ow
import FileLogger


sDict = {       '47000006C4507628': 'Tbojler',
                'BC000006C53F2928': 'Tsanitarna',
                '2C000006C3BCDB28': 'Tkamin',
                '6C000006C43A6228': 'Toutside',
                'DB0000067CF42828': 'Tinside',
                'BE000006C5856E28': 'Tcollector', }

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
GPIO.setup(27, GPIO.OUT)
GPIO.output(27,True) #Turn power OFF

global logger
logger = FileLogger.startLogger("/var/log/kolektor.log", 1000000, 5) 
state = True 
dictTemp = None
logger.info("Starting Logger...")

ow.init('localhost:4304')

"""i = 0
Sanitarna = 60
Kolektori = 30
"""
# endless loop, on/off for 1 second
while True:
	
	dictTemp = read_all_temp()
	if(dictTemp != -1):
        	if(float(dictTemp['Tsanitarna']) <= float(dictTemp['Tcollector']) - 8):
        		logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Pumpa ON')
			print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Tsanitarna <= Tkolektor-8 Pumpa ON')
			GPIO.output(27,False) #Turn power ON
			state = True


        	if(float(dictTemp['Tsanitarna']) > float(dictTemp['Tcollector']) - 2):	
			logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Pumpa OFF')
	        	print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Tsanitarna > Tkolektor-2 Pumpa OFF')
			GPIO.output(27,True) #Turn power OFF
			state = False

		logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Tkol ' + dictTemp['Tcollector'] + "\t" + 'Tsan ' + dictTemp['Tsanitarna'] + "\t" + 'Pump=' + str(state))
		print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Tkolektor ' + dictTemp['Tcollector'] + "\t" + 'Tsanitarna ' + dictTemp['Tsanitarna'] + "\t" + 'Kolektor pumpa ' + str(state))
	else:
		logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'dictTemp missing')
	time.sleep(10)

"""	if(Sanitarna <= Kolektori - 8):
        	print (strftime("[%H:%M:%S]: ", localtime()) + 'Kolektor pumpa ON')
		state = True

	if(Sanitarna > Kolektori - 2):
		print (strftime("[%H:%M:%S]: ", localtime()) + 'Kolektor pumpa OFF')
               	state = False

	print (strftime("[%H:%M:%S]: ", localtime()) + 'Tkolektor ' + str(Kolektori) + "\t" + 'Tsanitarna ' + str(Sanitarna) + "\t" + 'Kolektor pumpa ' + str(state))

	sleep(1)
	
	if(state):
		i += 1
		Kolektori -= 1
		Sanitarna += 1
	else:
		Kolektori += 1
		Sanitarna -= 1
		i -= 1

"""


