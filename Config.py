
# Plotly settings
plotlyEnable = True
#plotlyInterval = "2 day"				# Most recent interval of datapoint to display in integer days
plotlyIntervalDays = 2					# Most recent interval of datapoint to display in integer days
plotly_postinterval = 3*60				# Save data interval (sec)

# RPi Temp Sensor
RPiTempEnable = True
RPiTemp_postinterval = 3*60				# Save data interval (sec)
RPiTemp_plotlyinterval = 60				# Save data interval (sec)

HOME_AUTOMATION_ROOM_TEMPERATURE = 24
HOME_AUTOMATION_ROOM_TEMPERATURE_HYSTERESIS = 1
HOME_AUTOMATION_SANITARY_TEMPERATURE_HYSTERESIS = 1

sDict = {       '47000006C4507628': 'Tbojler',
                'BC000006C53F2928': 'Tsanitarna',
                '2C000006C3BCDB28': 'Tkamin',
                '6C000006C43A6228': 'Toutside',
                'DB0000067CF42828': 'Tinside',
				'BE000006C5856E28': 'Tcollector' }

