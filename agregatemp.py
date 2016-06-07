import sys
import os
import glob
#from time import time, sleep, localtime, strftime
import time
#import hanging_threads
#import threading
#import signal
#import traceback
#import Queue
import FileLogger
import MySQLdatabase
import ow
from Private import *
from Config import *

rpi_temp = None

def init():
	try:
		ow.init('localhost:4304')
		return True				
	except Exception, e:
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
				
		if logger:
			print (time.strftime("[%H:%M:%S]: ", time.localtime()) + str(sensorDict))
			
	except Exception, e:
		print (time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc())

		if logger:
			logger.error((time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc()), exc_info=True)
		return -1;
	return sensorDict	
		
print "Starting temperature agregator..."	

# Start File Logger
print "Starting Logger.."
global logger
logger = FileLogger.startLogger("/var/log/agregatemp.log", 1000000, 5)
logger.info("Starting Logger...")

# Initialize RPi_Temp module
if not init():
	print "Error: initializing RPi_Temp"
	sys.exit()

dictTemp = None
curFloorPump = None

while True:
	
	try:
		
		#read all sensors on one wire
		dictTemp = read_all_temp()
		if(dictTemp != -1):
			db = MySQLdatabase.Connect(mysql_host, mysql_login, mysql_pw, mysql_db)
			print dictTemp
			if (dictTemp != None):
				for SensorName in dictTemp:
					print (time.strftime("[%H:%M:%S]: ", time.localtime()) + SensorName + "\t" + str(dictTemp[SensorName]))
					MySQLdatabase.InsertData(db, 'sensordata', SensorName, 'Raspberry Pi', 'Current', 'Temperature', dictTemp[SensorName], 'C')
					if logger:
						logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + SensorName + "\t" + str(dictTemp[SensorName]))
					
			#BOILER PUMP
			if(float(dictTemp['Tsanitarna']) >= float(dictTemp['Tbojler']) + 1):
				#save to DB
				print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'BoilerPump' + "\t" + '0')
				MySQLdatabase.InsertData(db, 'sensordata', 'BoilerPump', 'Raspberry Pi', 'Current', 'Pump', '0', 'bool')
				if logger:
					logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'BoilerPump' + "\t" + '0')
		
			if(float(dictTemp['Tsanitarna']) <= float(dictTemp['Tbojler']) - 1):
				#save to DB
				print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'BoilerPump' + "\t" + '1')
				MySQLdatabase.InsertData(db, 'sensordata', 'BoilerPump', 'Raspberry Pi', 'Current', 'Pump', '1', 'bool')
				if logger:
					logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'BoilerPump' + "\t" + '1')
							
			#FLOOR PUMP
			if 'Tinside' in dictTemp:
				if((float(dictTemp['Tinside']) >= 25) or (curFloorPump == None)):
					#save to DB
					print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'FloorPump' + "\t" + '0')
					MySQLdatabase.InsertData(db, 'sensordata', 'FloorPump', 'Raspberry Pi', 'Current', 'Pump', '0', 'bool')
					if logger:
						logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'FloorPump' + "\t" + '0')
					if curFloorPump != None:
						curFloorPump = 0
			else:
				print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Sensor Tinside missing')
				if logger:
                                        logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'Sensor Tinside missing')
				
			if 'Tinside' in dictTemp:
				if(float(dictTemp['Tinside']) <= 23):
					#save to DB
					print (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'FloorPump' + "\t" + '1')
					MySQLdatabase.InsertData(db, 'sensordata', 'FloorPump', 'Raspberry Pi', 'Current', 'Pump', '1', 'bool')
					if logger:
						logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'FloorPump' + "\t" + '1')
					curFloorPump = 1
		
			MySQLdatabase.Close(db)
		else:
			 if logger:
                         	logger.info (time.strftime("[%H:%M:%S]: ", time.localtime()) + 'dictTemp missing!')
		time.sleep(RPiTemp_postinterval)

	except IOError, e:
		print (time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc())

		if logger:
			logger.error((time.strftime("[%H:%M:%S]: EXCEPTION ", time.localtime()) + traceback.format_exc()), exc_info=True)
		#sys.exit()

							
					

	
	
		
	

