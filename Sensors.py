import ow

ow.init('localhost:4304')

sDict = { 	'47000006C4507628': 'Tbojler',
			'BC000006C53F2928': 'Tsanitarna',
			'2C000006C3BCDB28': 'Tkamin', 
			'6C000006C43A6228': 'Toutside',
			'DB0000067CF42828': 'Tinside', 
			'BE000006C5856E28': 'Tcollector', }

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
#create dictionary
#sensorDict = {}
#for sensor in sensors:
#	if sensor.r_address in sDict:
#		#Sensor has name defined
#		sensorDict[sDict[sensor.r_address]] = "%.2f" % float(sensor.temperature)
#	else:
#		#Sensor name missing. Creating new one
#		sensorDict['T_' + sensor.r_address] = "%.2f" % float(sensor.temperature)
#print (sensorDict)
