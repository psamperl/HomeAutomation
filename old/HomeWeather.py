import sys
import signal
import threading
import traceback
import Queue
from time import time, sleep, localtime, strftime
from datetime import datetime
from threading import Timer
import FileLogger
import RPi_Temp
import plotlyClient
import MySQLdatabase
from Private import *
from Config import *


def main():
	
	# Start File Logger
	print "Starting Logger.."
	logger = FileLogger.startLogger("/var/log/HomeWeather.log", 1000000, 5)
	logger.info("Starting Logger...")
	
	# Check for internet connection
	#URL = "http://www.google.com"
	#print "Checking for internet connection..."
	#logger.info("Checking for internet connection...")
	#for retry in range(10):
	#	try:
	#		response = requests.get(URL)
	#	except Exception as e:
	#		print "Failed to connect to Internet"
	#		print e
	#		logger.error("Failed to connect to Internet", exc_info=True)
	#		sleep(3)
	#	if response.ok:
	#		break

	lock = threading.Lock()

	# Initialize sensors
	if not initSensors(lock, logger):
		cleanup()
		sys.exit()
	#sleep(30)				# wait for sensors to initialize
	
	# Initialize plotly
	if not initPlotly(lock, logger):
		cleanup()
		sys.exit()

	# Setup exit handlers
	signal.signal(signal.SIGTSTP, SIGTSTP_handler)
	signal.signal(signal.SIGINT, SIGINT_handler)
	
	# Wait for termination
	signal.pause()
	

def initSensors(lock, logger=None):

	# Init MySQLdb
	db = MySQLdatabase.Connect(mysql_host, mysql_login, mysql_pw, mysql_db)
	if (db == None):
		print (strftime("[%H:%M:%S]: Error: Cannot connect to MySQL database", localtime()))
		if logger:
			logger.error(strftime("[%H:%M:%S]: Error: Cannot connect to MySQL database", localtime()), exc_info=True)
		return False

	# RPi Temp Sensor
	qIn_RPiTemp= Queue.Queue()
	qOut_RPiTemp = Queue.Queue()
        
	if RPiTempEnable:
		rpi_temp = RPi_Temp.RPi_Temp(lock, qIn_RPiTemp, qOut_RPiTemp, logger)

		# Initialize RPi_Temp module
		if not rpi_temp.init():
			print (strftime("[%H:%M:%S]: Error: initializing RPi Temp", localtime()))
			if logger:
				logger.error(strftime("[%H:%M:%S]: Error: initializing RPi Temp", localtime()), exc_info=True)
			return False

		#rpi_temp.run()					# run on main thread
		rpi_temp.daemon = True

		rpi_temp.start()					# start thread

		#sleep(5)

	return True


def initPlotly(lock, logger=None):
	qIn_plotly= Queue.Queue()
	qOut_plotly = Queue.Queue()

	if plotlyEnable:
		plotlyclient = plotlyClient.plotlyClient(lock, qIn_plotly, qOut_plotly, logger)

		# Initialize plotlyClient module
		if not plotlyclient.init():
			print (plotlyclient("[%H:%M:%S]: Error: initializing plotlyClient", localtime()))
			if logger:
				logger.error(strftime("[%H:%M:%S]: Error: initializing plotlyClient", localtime()), exc_info=True)
			return False

		#plotlyclient.run()					# run on main thread
		plotlyclient.daemon = True
		plotlyclient.start()				# start thread
	
	return True
	

def SIGTSTP_handler(signum, frame):
	print 'SDIGTSTP detected!'
	sys.exit(0)

def SIGINT_handler(signum, frame):
	print 'SIGINT detected!'
	sys.exit(0)
	

def cleanup():
	print "Clean up..."
	
	
if __name__ == "__main__":
	main()
	
