import ow
from Config import *

ow.init('localhost:4304')


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
		print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

	return sensorDict	

Dict = read_all_temp()
print (Dict)
