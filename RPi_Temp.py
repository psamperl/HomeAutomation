import sys
import os
import glob
from time import time, sleep, localtime, strftime
import hanging_threads
import threading
import signal
import traceback
import Queue
import FileLogger
import MySQLdatabase
import ow
from Credentials import *
from Config import *

rpi_temp = None

def main():

	# Setup exit handlers
	signal.signal(signal.SIGTSTP, SIGTSTP_handler)
	signal.signal(signal.SIGINT, SIGINT_handler)
	
	lock = threading.Lock()
	qIn = Queue.Queue()
	qOut = Queue.Queue()

	# Start File Logger
	print "Starting Logger.."
	global logger
	logger = FileLogger.startLogger("/var/log/RPi_Temp.log", 1000000, 5)
	logger.info("Starting Logger...")

	global rpi_temp
	rpi_temp = RPi_Temp(lock, qIn, qOut, logger)

	# Initialize RPi_Temp module
	if not rpi_temp.init():
		print "Error: initializing RPi_Temp"
		sys.exit()

	#rpi_temp.run()					# run on main thread
	rpi_temp.start()					# start thread

	# Pass message to child
	msg = message()
	msg.timestamp = time()
	msg.command = "measure:temp?"
	msg.argument = ""
	qIn.put(msg)

	# Monitor for messages from child
	while True:
		if not qOut.empty():
			msg = qOut.get()
			if isinstance(msg, message):
				print (strftime("[%H:%M:%S]: ", localtime()) + "Message from RPi_Temp\t" + str(msg.command) +"\t" + str(msg.argument))
				logger.info (strftime("[%H:%M:%S]: ", localtime()) + "Message from RPi_Temp\t" + str(msg.command) +"\t" + str(msg.argument))
		sleep(0.1)

	rpi_temp.join()
	
	# Wait for termination
	signal.pause()
	

def SIGTSTP_handler(signum, frame):
	print 'SDIGTSTP detected!'
	cleanup()
	sys.exit(0)

def SIGINT_handler(signum, frame):
	print 'SIGINT detected!'
	cleanup()
	sys.exit(0)

def cleanup():
	global rpi_temp
	if rpi_temp:
		rpi_temp.stop()
	
class RPi_Temp(threading.Thread):
	""" Read Raspberry Pi temperature sensor at defined interval and posts to database
		Latest reading can be queried through queue

		Ask the thread to stop by calling its stop() method.
    """
	def __init__(self, lock, qIn=None, qOut=None, logger=None):
		super(RPi_Temp, self).__init__()
		self.lock = lock
		self.qIn = qIn										# Incoming messages
		self.qOut = qOut									# Outgoing messages
		self.logger = logger								# Output log
		self.stoprequest = threading.Event()				# Stop thread flag

		self.postinterval = RPiTemp_postinterval			# Save data interval

	def init(self):
		try:
			ow.init('localhost:4304')
			return True				
		except Exception, e:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
		  		return False		        
			#sys.exit()
		

	def run(self):
		print "Starting RPi Temp thread..."

		# Initialize
		#self.device_file = self.initTemp()
		#if not self.device_file:
		#	print (strftime("[%H:%M:%S]: Error: cannot initialize RPi Temp Sensor ", localtime()))

		# Subtract post interval to get immediate reading in loop below
		currentposttime = time() - self.postinterval

		curTime = None
		curTemp = None
		dictTemp = None

		while True:

			try:
				if self.stoprequest.isSet():
					break

				# Save current measurement to database
				if (time() - currentposttime) > self.postinterval:
					currentposttime = time()

					try:
		
						self.lock.acquire()
						if self.logger:
							self.logger.info (strftime("[%H:%M:%S]: ", localtime()) + "RPi_Temp lock acquired")

						db = MySQLdatabase.Connect(mysql_host, mysql_login, mysql_pw, mysql_db)

						curTime = time()
						
						#read all sensors on one wire
						dictTemp = self.read_all_temp()
						if (dictTemp != None):
							for SensorName in dictTemp:
								print (strftime("[%H:%M:%S]: ", localtime()) + SensorName + "\t" + str(dictTemp[SensorName]))
								MySQLdatabase.InsertData(db, 'sensordata', SensorName, 'Raspberry Pi', 'Current', 'Temperature', dictTemp[SensorName], 'C')
								if self.logger:
									self.logger.info (strftime("[%H:%M:%S]: ", localtime()) + SensorName + "\t" + str(dictTemp[SensorName]))
						'''
						curTemp = self.read_temp()
						if (curTemp != None):
							print (strftime("[%H:%M:%S]: ", localtime()) + "2nd Floor Temp\t" + str(curTemp))
							MySQLdatabase.InsertData(db, 'sensordata', '2nd Floor', 'Raspberry Pi', 'Current', 'Temperature', "%.2f" % float(curTemp), 'C')
							if self.logger:
								self.logger.info (strftime("[%H:%M:%S]: ", localtime()) + "2nd Floor Temp\t" + str(curTemp))
						'''
						MySQLdatabase.Close(db)

						self.sendMessage(curTime, 'RPi_Temp', 'measure:temp', curTemp)


					except IOError, e:
						print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

						if self.logger:
							self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
						#sys.exit()
					
					self.lock.release()
					if self.logger:
						self.logger.info (strftime("[%H:%M:%S]: ", localtime()) + "RPi_Temp lock released")


				# Check incoming message queue
				if self.qIn:
					while not self.qIn.empty():
						msg = self.qIn.get()
						if isinstance(msg, message):
							if msg.command == 'measure:temp?':
								self.sendMessage(curTime, 'RPi_Temp', 'measure:temp', curTemp)
						else:
							print "Error: unknown object in queue"
							if self.logger:
								self.logger.error(strftime("[%H:%M:%S]: ", localtime()) + "Error: unknown object in queue")
									
				sleep(0.1)				

			except Exception, e:
				print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

				if self.logger:
					self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
				#sys.exit()


	def stop(self, timeout=None):
		self.stoprequest.set()
		super(Rpi_Temp, self).join(timeout)


	def sendMessage(self, time, source, command, argument):
		msgOut = message()
		msgOut.timestamp = time
		msgOut.source = source
		msgOut.command = command
		msgOut.argument = argument

		if self.qOut and not self.qOut.full():
			self.qOut.put(msgOut)

	#read temperatures
	def read_temp(self):
		sensors = ow.Sensor("/").sensorList()

		for sensor in sensors[:]:	
			if sensor.type != 'DS18B20':
				sensors.remove( sensor )

		for sensor in sensors:
			if sensor.r_address == '47000006C4507628':
				Tbojler = sensor.temperature
			if sensor.r_address == 'BC000006C53F2928':
				Tfireplace = sensor.temperature
			if sensor.r_address == '2C000006C3BCDB28':
				Tkamin = sensor.temperature 

		# show only one decimal place for temprature
		temp_C = "%.2f" % float(Tbojler)
		fireplace_C = "%.2f" % float(Tfireplace)
		kamin_C = "%.2f" % float(Tkamin)	
		if self.logger:
			print (strftime("[%H:%M:%S]: ", localtime()) + "Tsanitarna\t" + str(temp_C))
		return temp_C
		
	#read all temperatures
	def read_all_temp(self):
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
					
			if self.logger:
				print (strftime("[%H:%M:%S]: ", localtime()) + str(sensorDict))
				
		except Exception, e:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)

		return sensorDict	

class message:
	timestamp = None
	source = None
	command = None
	argument = None


if __name__ == '__main__':
	main()
