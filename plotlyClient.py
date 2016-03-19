 #!/usr/bin/python
 # -*- coding: utf-8 -*-

import plotly
from plotly import tools
from plotly.graph_objs import *
import plotly.graph_objs as go
import sys
import os
from time import time, sleep, localtime, strftime
import hanging_threads
import threading
import signal
import traceback
import Queue
import FileLogger
import MySQLdatabase
from Credentials import *
from Config import *

plotlyclient = None

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
	logger = FileLogger.startLogger("/var/log/plotlyClient.log", 1000000, 5)
	logger.info("Starting Logger...")

	plotlyclient = plotlyClient(lock, qIn, qOut, logger)

	# Initialize plotlyClient module
	if not plotlyclient.init():
		print "Error: initializing plotlyClient"
		sys.exit()

	#plotlyclient.run()					# run on main thread
	plotlyclient.start()				# start thread

	# Pass message to child
	msg = message()
	msg.timestamp = time()
	msg.command = ""
	msg.argument = ""
	qIn.put(msg)

	# Monitor for messages from child
	while True:
		if not qOut.empty():
			msg = qOut.get()
			if isinstance(msg, message):
				print (strftime("[%H:%M:%S]: ", localtime()) + "Message from plotlyClient\t" + str(msg.command) +"\t" + str(msg.argument))
				logger.info (strftime("[%H:%M:%S]: ", localtime()) + "Message from plotlyClient\t" + str(msg.command) +"\t" + str(msg.argument))
		sleep(0.1)

	plotlyClient.join()
	
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
	global plotlyclient
	if plotlyclient:
		plotlyclient.stop()
	
class plotlyClient(threading.Thread):
	""" Read sensor data from database at defined interval and posts to plotly

		Ask the thread to stop by calling its stop() method.
    """

	def __init__(self, lock, qIn=None, qOut=None, logger=None):
		super(plotlyClient, self).__init__()
		self.lock = lock
		self.qIn = qIn										# Incoming messages
		self.qOut = qOut									# Outgoing messages
		self.logger = logger								# Output log
		self.stoprequest = threading.Event()				# Stop thread flag

		self.postinterval = plotly_postinterval				# Save data interval
		self.plotlyInterval = plotlyIntervalDays			# Most recent interval of datapoint to display in integer days
		self.debug = True

		self.fontlist = '\"Avant Garde\", Avantgarde, \"Century Gothic\", CenturyGothic, \"AppleGothic\", sans-serif'

		self.legendstyle = {
			"bgcolor": 'rgba(0, 0, 0, 0)',	#transparent
			"bordercolor": 'rgba(0, 0, 0, 0)',	#transparent
			"borderwidth": 0,
			"font":{
				'family': self.fontlist,
				'size': 12,
				'color': 'black'
			}
		}

		self.layout = {
		  "title" : "Pi Heating",

		 'titlefont': { 
			'family':self.fontlist,
			'size': 25,
			'color': "black"
			},

		'autosize': True, 
		'width': 1000, 
		'height': 900, 
		'margin':{
			'l': 80,
			'r': 170,
			't': 80,
			'b': 80,
			'pad': 2 
			}, 

		#global font
		'font': {
		  'family': self.fontlist,
		  'size': 12,
		  'color': "black"
		  },
  
		  "xaxis": {
			"title": "Time",
			"titlefont": {
			  "family": self.fontlist,
			  "size": 18,
			  "color": "black"
			},
			"anchor": "y",
			"domain": [0, 1],
			"position": 0,
		  },
		  
		  "xaxis2": {
			"title": "Devices",
			"titlefont": {
			  "family": self.fontlist,
			  "size": 18,
			  "color": "black"
			},
			"anchor": "y",
			"domain": [0, 1],
			"position": 0,
		  },

		  "yaxis": {
			"domain": [0.7, 1],
			"title": "Temperature (C)",
			"titlefont": {
			  "family": self.fontlist,
			  "size": 18,
			  "color": "black"
			},
			"position": 0,
			"overlaying": "False",
		  },
		  
		  "yaxis2": {
			"domain": [0, 0.2],
			"title": "State [0,1]",
			"titlefont": {
			  "family": self.fontlist,
			  "size": 18,
			  "color": "black"
			},
			"position": 0,
			"overlaying": "False",
			"range": [0, 1],
		  },
		  
		  "paper_bgcolor": "white",
		  "plot_bgcolor": "white",

		  "showlegend": True,
		  "legend": self.legendstyle,
  
  
		   'annotations': [	]
		}

		self.annotation_link = {
			'text':"<i><b>View the code used</b></i><i><b> to generate this plot <a href = 'https://github.com/flann321/HomeCoolingPi'> here</a></b></i>",
			'x':1.0,
			'y':-0.05,
			'showarrow':False,
			'ref':'paper',
			'align':'left',
			'font':{
					   'size':'12'
				   }
		}

		self.annotation_template = {
			'text':"",
			'bordercolor':"rgba(0, 0, 0, 0)",
			'borderwidth':2.9,
			'borderpad':1,
			'bgcolor':"rgba(0, 0, 0, 0)",
			'xref':"x",
			'yref':"y",
			'showarrow':True,
			'arrowwidth':2,
			'arrowcolor':"",
			'arrowhead':1,
			'arrowsize':1,
			'textangle':0,
			'tag':"",
			'font':{
				'family':"",
				'size':20,
				'color':"rgb(0, 0, 0)"
			},
			'opacity':1,
			'align':"center",
			'xanchor':"auto",
			'yanchor':"auto",
			'y':0,
			'x':0,
			'ay':0,
			'ax':0
		}

		self.annot1 = {'opacity': 1, 'yanchor': 'auto', 'text': '\xe2\x98\x80\xef\xb8\x8e', 'arrowsize': 1, 'tag': '', 'borderwidth': 2.9, 'ay': 0, 'ax': 0, 'font': {'color': 'rgb(0, 0, 0)', 'family': '', 'size': 20}, 'arrowcolor': '', 'xref': 'x', 'arrowhead': 1, 'bgcolor': 'rgba(0, 0, 0, 0)', 'borderpad': 1, 'showarrow': True, 'bordercolor': 'rgba(0, 0, 0, 0)', 'xanchor': 'auto', 'arrowwidth': 2, 'yref': 'y', 'align': 'center', 'textangle': 0, 'y': 95.905, 'x': 1410701712000.0}
		self.annot2 = {'opacity': 1, 'yanchor': 'auto', 'text': '\xe2\x98\x80\xef\xb8\x8e', 'arrowsize': 1, 'tag': '', 'borderwidth': 2.9, 'ay': 0, 'ax': 0, 'font': {'color': 'rgb(0, 0, 0)', 'family': '', 'size': 20}, 'arrowcolor': '', 'xref': 'x', 'arrowhead': 1, 'bgcolor': 'rgba(0, 0, 0, 0)', 'borderpad': 1, 'showarrow': True, 'bordercolor': 'rgba(0, 0, 0, 0)', 'xanchor': 'auto', 'arrowwidth': 2, 'yref': 'y', 'align': 'center', 'textangle': 0, 'y': 95.905, 'x': 1410660135000.0}


	def init(self):
		py = self.initPlotly(plotly_un, plotly_key)
		if py == False: return False
		
		#retVal = self.GetSQLData(plotlyIntervalDays)
		#if retVal == False: return False
		
		return True


	def run(self):
		print strftime("[%H:%M:%S]: ", localtime()) + "Starting plotly Client..."	
	
		# Init plotly handle
		if self.debug: print strftime("[%H:%M:%S]: ", localtime()) + "initPlotly"
		py = self.initPlotly(plotly_un, plotly_key)
		

		# Subtract post interval to get immediate reading in loop below
		currentposttime = time() - self.postinterval

		while True:

			try:
				if self.stoprequest.isSet():
					break

				# Save current measurement to database
				if (time() - currentposttime) > self.postinterval:
					currentposttime = time()

					self.lock.acquire()
					if self.logger:
						self.logger.info (strftime("[%H:%M:%S]: ", localtime()) + "plotlyClient lock acquired")

					try:
		
						# Init MySQLdb
						if self.logger: self.logger.info(strftime("[%H:%M:%S]: ", localtime()) + "MySQL connect")
						db = MySQLdatabase.Connect(mysql_host, mysql_login, mysql_pw, mysql_db)
						if (db == None):
							return

						if self.logger: self.logger.info(strftime("[%H:%M:%S]: ", localtime()) + "Post SQL data to plotly")
						starttime = time()
						interval = str(self.plotlyInterval) + ' day'
						self.PostArraySQL(py, db, interval)
						endtime = time()
						if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Plotly post time %s sec" % (endtime-starttime))

						MySQLdatabase.Close(db)

					except IOError, e:
						print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

						if self.logger:
							self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
						#sys.exit()

					self.lock.release()
					if self.logger:
						self.logger.info (strftime("[%H:%M:%S]: ", localtime()) + "plotlyClient lock released")

				# Check incoming message queue
				if self.qIn:
					while not self.qIn.empty():
						msg = self.qIn.get()
						if isinstance(msg, message):
							if msg.command == 'measure:temp?':
								msgOut = message()
								msgOut.timestamp = time()
								msgOut.command = 'measure:temp'
								msgOut.argument = curTemp

								if (self.qOut and not self.qOut.full()):
									self.qOut.put(msgOut)
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
		super(plotlyClient, self).join(timeout)


	def initPlotly(self, plotly_un, plotly_key):
		try:
			#Plotly credentials
			plotly.tools.set_credentials_file(username=plotly_un, api_key=plotly_key)
			#Plotly handle
			py = plotly.plotly
		except:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
			return False

		return py

	# Get all the stored data from SQL
	def GetSQLData(self, db, intervalDays):
		self.DataPoints = {}
		interval = str(intervalDays) + ' day'

		try:
			'''if self.debug: print strftime("[%H:%M:%S]: ", localtime()) + "RPi Temperature"
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, '2nd Floor', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
			self.DataPoints["RPi Temperature"] = (ts, value)
			'''
			#Zalogovnik
			if self.debug: print strftime("[%H:%M:%S]: ", localtime()) + "Tbojler"
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Tbojler', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
			self.DataPoints["Tbojler"] = (ts, value)
			
			#Kamin
			if self.debug: print strftime("[%H:%M:%S]: ", localtime()) + "Tkamin"
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Tkamin', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
			self.DataPoints["Tkamin"] = (ts, value)
			
			#Sanitarna
			if self.debug: print strftime("[%H:%M:%S]: ", localtime()) + "Tsanitarna"
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Tsanitarna', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
			self.DataPoints["Tsanitarna"] = (ts, value)
			
			#Outside
			if self.debug: print strftime("[%H:%M:%S]: ", localtime()) + "Toutside"
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Toutside', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
			self.DataPoints["Toutside"] = (ts, value)
			
			#Inside
			if self.debug: print strftime("[%H:%M:%S]: ", localtime()) + "Tinside"
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Tinside', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
			self.DataPoints["Tinside"] = (ts, value)
			
			#Collector
			if self.debug: print strftime("[%H:%M:%S]: ", localtime()) + "Tcollector"
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Tcollector', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
			self.DataPoints["Tcollector"] = (ts, value)

			self.PurgeOldDataPoints(intervalDays)
			
		except:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())
			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
			return False

		return True

	# Purge data points older than interval
	# interval : int
	# 	interval in days
	def PurgeOldDataPoints(self, interval):
		td = datetime.timedelta(days=interval)
		timelimit = time() - td.total_seconds()
		
		for key in self.DataPoints:
			(ts, value) = self.DataPoints[key]
			for i in range(len(ts)):
				if ts[i] >= timelimit:
					del ts[0:i]
					del value[0:i]
					break
			

	# Convert SQL query result into series data
	def GenerateDataPoints(self, queryresult):
		ts = []
		value = []
		for entry in queryresult:
			ts.append(str(entry[MySQLdatabase.timestamp]))
			value.append(entry[MySQLdatabase.data])

		return (ts, value)

	# Generate the sunrise/sunset times as annotation list
	# Input the SQL query and annotation text
	# Returns list of annotations if found
	# else returns None
	def GenerateSunAnnotation(self, queryresult, annot_text=None, y=0, color='black'):
		#print "Generate Sun Annotation"
		#print 'color: ' + color
	
		annot = []
		#del(annot)
		#annot = []
	
		suntimesdict = {}
		#del(suntimesdict)
		#suntimesdict = {}
	
		(ts, value) = self.GenerateDataPoints(queryresult)

		# add datapoints to dictionary
		for suntime in value:

			#print "suntime"
			#print suntime
			#print ts[0]
			#print ts[len(ts)-1]
			#print suntime >= ts[0]
			#print suntime <= ts[len(ts)-1]

			dtstart = datetime.strptime(ts[0], '%Y-%m-%d %H:%M:%S')
			dtend = datetime.strptime(ts[len(ts)-1], '%Y-%m-%d %H:%M:%S')
			dtsuntime = datetime.fromtimestamp(suntime)

			#print dtstart
			#print dtend
			#print dtsuntime

			# only add datapoints that are within the 
			# given query timestamps will be plotted
			if dtsuntime >= dtstart and dtsuntime <= dtend:
				suntimesdict[suntime] = None	

		#print "dictionary: "
		#print suntimesdict

		for suntime in suntimesdict.keys():
			#ts = datetime.fromtimestamp(int(suntime)).strftime('%Y-%m-%d %H:%M:%S')
			#print "suntimesdict loop"
		
			annotation = self.annotation_template.copy()	# must copy dictionary explicitly
			annotation['text'] = annot_text
			annotation['x'] = suntime * 1000	# multiply by 1000 for plotly
			annotation['y'] = y
			annotation['ax'] = 0
			annotation['ay'] = 0
			annotation['font']['color'] = color
		
			#debug code
			#print 'annotation'
			#print annotation

			annot.append(annotation)
	
		#debug code
		#print 'annot'
		#print annot
	
		if annot == []:
			return None
		else:
			return annot

	# Generate pump markers
	# Input the SQL query and annotation text
	# Returns list of annotations if found
	# else returns None
	def GenerateDeviceMarkers(self, queryresult, annot_text=None, y=0, color='black'):
		#print "Generate Sun Annotation"
		#print 'color: ' + color
	
		annot = []
		#del(annot)
		#annot = []
	
		suntimesdict = {}
		#del(suntimesdict)
		#suntimesdict = {}
	
		(ts, value) = self.GenerateDataPoints(queryresult)

		# add datapoints to dictionary
		for suntime in value:

			#print "suntime"
			#print suntime
			#print ts[0]
			#print ts[len(ts)-1]
			#print suntime >= ts[0]
			#print suntime <= ts[len(ts)-1]

			dtstart = datetime.strptime(ts[0], '%Y-%m-%d %H:%M:%S')
			dtend = datetime.strptime(ts[len(ts)-1], '%Y-%m-%d %H:%M:%S')
			dtsuntime = datetime.fromtimestamp(suntime)

			#print dtstart
			#print dtend
			#print dtsuntime

			# only add datapoints that are within the 
			# given query timestamps will be plotted
			if dtsuntime >= dtstart and dtsuntime <= dtend:
				suntimesdict[suntime] = None	

		#print "dictionary: "
		#print suntimesdict

		for suntime in suntimesdict.keys():
			#ts = datetime.fromtimestamp(int(suntime)).strftime('%Y-%m-%d %H:%M:%S')
			#print "suntimesdict loop"
		
			annotation = self.annotation_template.copy()	# must copy dictionary explicitly
			annotation['text'] = annot_text
			annotation['x'] = suntime * 1000	# multiply by 1000 for plotly
			annotation['y'] = y
			annotation['ax'] = 0
			annotation['ay'] = 0
			annotation['font']['color'] = color
		
			#debug code
			#print 'annotation'
			#print annotation

			annot.append(annotation)
	
		#debug code
		#print 'annot'
		#print annot
	
		if annot == []:
			return None
		else:
			return annot			

	#Format data and send to plotly
	def PostData(self, py):

		trace1 = []
		trace2 = []
		trace3 = []
		'''
		series = {
			'name' : '2nd Floor Temperature (Raspberry Pi)',
			'x' : self.DataPoints["RPi Temperature"][0],
			'y' : self.DataPoints["RPi Temperature"][1],
			'type' : 'scatter',
			'mode' : 'lines'
			}
		data.append(series)
		'''	
		series = {
			'name' : 'Tbojler',
			'x' : self.DataPoints["Tbojler"][0],
			'y' : self.DataPoints["Tbojler"][1],
			'type' : 'scatter',
			'mode' : 'lines'
			}
		trace1.append(series)
		
		series = {
			'name' : 'Tkamin',
			'x' : self.DataPoints["Tkamin"][0],
			'y' : self.DataPoints["Tkamin"][1],
			'type' : 'scatter',
			'mode' : 'lines'
			}
		trace1.append(series)
		
		series = {
			'name' : 'Tsanitarna',
			'x' : self.DataPoints["Tsanitarna"][0],
			'y' : self.DataPoints["Tsanitarna"][1],
			'type' : 'scatter',
			'mode' : 'lines'
			}
		trace1.append(series)
		
		series = {
			'name' : 'Toutside',
			'x' : self.DataPoints["Toutside"][0],
			'y' : self.DataPoints["Toutside"][1],
			'type' : 'scatter',
			'mode' : 'lines'
			}
		trace1.append(series)
		
		series = {
			'name' : 'Tinside',
			'x' : self.DataPoints["Tinside"][0],
			'y' : self.DataPoints["Tinside"][1],
			'type' : 'scatter',
			'mode' : 'lines'
			}
		trace1.append(series)
		
		series = {
			'name' : 'Tcollector',
			'x' : self.DataPoints["Tcollector"][0],
			'y' : self.DataPoints["Tcollector"][1],
			'type' : 'scatter',
			'mode' : 'lines'
			}
		trace1.append(series)
		
		series = {
			'name' : 'BoilerPump',
			'x' : self.DataPoints["BoilerPump"][0],
			'y' : self.DataPoints["BoilerPump"][1],
			'type' : 'scatter',
			'mode' : 'lines'
			}
		trace2.append(series)
		
		series = {
			'name' : 'FloorPump',
			'x' : self.DataPoints["FloorPump"][0],
			'y' : self.DataPoints["FloorPump"][1],
			'type' : 'scatter',
			'mode' : 'lines'
			}
		trace3.append(series)

		try:
			
			# Send data to plotly
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Plotly Post")
			data = Data([trace1, trace2])
			fig = Figure(data=trace1, layout=self.layout)
			response = py.plot(fig, filename='myplot')

		except:
			print (strftime("[%H:%M:%S]: PostData EXCEPTION ", localtime()) + traceback.format_exc())
		
			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: PostData EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)



	#Post data from SQL queries and send to plotly
	def PostArraySQL(self, py, db, interval):

		trace1 = []
		trace2 = []
		trace3 = []
		trace4 = []
		trace5 = []
		trace6 = []
		trace7 = []
		trace8 = []
				
		try:
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Tbojler")
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Tbojler', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
		except:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
		trace1 = go.Scatter({
			'x' : ts,
			'y' : value,
			'name' : 'Heat Storage',
			})
		#trace1.append(series)
		
		
		try:
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Tkamin")
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Tkamin', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
		except:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
		trace3 = {
			'x' : ts,
			'y' : value,
			'name' : 'Fireplace',
			}
		#trace1.append(series)
		
		try:
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Tsanitarna")
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Tsanitarna', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
		except:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
		trace4 = {
			'x' : ts,
			'y' : value,
			'name' : 'Sanitary',
			}
		#trace1.append(series)

		try:
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Toutside")
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Toutside', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
		except:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
		trace5 = {
			'x' : ts,
			'y' : value,
			'name' : 'Outside',
			'line':{
				'shape' : 'spline',
			},
			}
		#trace1.append(series)
		
		try:
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Tinside")
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Tinside', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
		except:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())
			
			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
		trace6 = {
			'x' : ts,
			'y' : value,
			'name' : 'Inside',
			'line':{
				'shape' : 'spline',
			},
			}
		
		try:
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "BoilerPump")
			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'BoilerPump', 'Raspberry Pi', 'Current', 'Pump')
			(ts, value) = self.GenerateDataPoints(result)
		except:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
		trace2 = go.Scatter({
			'x' : ts,
			'y' : value,
			'name' : 'Storage Pump',
			'line':{
				'shape' : 'hv',
			},
			'mode' : 'lines',
			})
		#trace2.append(series)
		
		try:
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "FloorPump")

			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'FloorPump', 'Raspberry Pi', 'Current', 'Pump')
			(ts, value) = self.GenerateDataPoints(result)
		except:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
		trace7 = go.Scatter({
			'x' : ts,
			'y' : value,
			'name' : 'Floor Pump',
			'line':{
				'shape' : 'hv',
			},
			'mode' : 'lines',
			})
			
		try:
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Tcollector")

			result = MySQLdatabase.QueryDataInterval(db, 'sensordata', interval, 'Tcollector', 'Raspberry Pi', 'Current', 'Temperature')
			(ts, value) = self.GenerateDataPoints(result)
		except:
			print (strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc())

			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)
		trace8 = {
			'x' : ts,
			'y' : value,
			'name' : 'Tcollector',
			'line':{
				'shape' : 'spline',
			},
			}
		
		try:
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Start composing figures")

			fig = tools.make_subplots(rows=3, cols=1, subplot_titles=('Temperature (C)', ''))
			fig.append_trace(trace1, 1, 1) #Storage
			fig.append_trace(trace3, 1, 1) #Fireplace
			fig.append_trace(trace4, 1, 1) #sanitary
			fig.append_trace(trace6, 1, 1) #Inside
			fig.append_trace(trace5, 1, 1) #Outside
			fig.append_trace(trace8, 1, 1) #Collector
			fig.append_trace(trace7, 2, 1) #Floor Pump
			fig.append_trace(trace2, 3, 1) #Heat Pump
			

			fig['layout']['yaxis1'].update(domain=[0.5, 1])
			fig['layout']['xaxis1'].update(showticklabels=False)
			#fig['layout']['yaxis2'].update(domain=[0.3, 0.5])
			#fig['layout']['xaxis2'].update(showticklabels=False)
			fig['layout']['yaxis2'].update(range=[0, 1], dtick=1, domain=[0.2, 0.3])
			fig['layout']['xaxis2'].update(showticklabels=False)
			fig['layout']['yaxis3'].update(range=[0, 1], dtick=1, domain=[0, 0.1])


        
 			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "End composing")       
			


			#print(fig['layout']['yaxis2'])

			fig['layout'].update(height=1000, width=600, title='Pi Home Automation')
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Plotly update...")
			response = py.plot(fig, filename='myplot')
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Plot")
			if self.logger: self.logger.info( strftime("[%H:%M:%S]: ", localtime()) + "Response: " + response)
			
		except:
			print (strftime("[%H:%M:%S]: PostArraySQL EXCEPTION ", localtime()) + traceback.format_exc())
		
			if self.logger:
				self.logger.error((strftime("[%H:%M:%S]: PostArraySQL EXCEPTION ", localtime()) + traceback.format_exc()), exc_info=True)


				

class message:
	timestamp = None
	command = None
	argument = None


if __name__ == '__main__':
	main()

