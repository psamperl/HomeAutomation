https://github.com/psamperl/HomeAutomation/blob/master/old/1.jpg
https://github.com/psamperl/HomeAutomation/blob/master/old/2.jpg
https://github.com/psamperl/HomeAutomation/blob/master/old/3.png

#PURPOSE
 fireplace.py
	checks if fireplace temperature is bigger than boiler.
	Acts as a differential thermostat by switching a pump
 kolektor.py
	Checks if collector temperature is bigger than boiler.
	Acts as a differential thermostat by switching a pump
 ubiClient.py
	Collects all temperature from 1wire sensors using OWFS and sends it to Ubidots
 getSensorVal.py
	Used to debug or when adding new sensors to the system.
	Prints out all sensors IDs and values
 
 
 fireplace_check.sh - Keeps fireplace.py running and sends alert if restarted
 kolektor_check.sh - keeps kolektor.py running and sends alert if restarted
 ubiClient_check.sh - keeps ubiClient.py running and sends alert if restarted

#USED
 - RPI,
 - SPI 1wire module http://www.sheepwalkelectronics.co.uk/product_info.php?cPath=22&products_id=67
 - 1wire sensors
 - relay board for pumps
 - OWFS to get temperatures from 1wire sensors
 - python
 - bash
 - ubidots
 
 
#HOW TO SETUP
	sudo raspi/config (enable spi and i2c)
	sudo reboot
	passwd
	sudo apt-get update
	sudo apt-get install python-smbus python3-smbus python-dev python3-dev
	sudo apt-get install i2c-tools
	sudo reboot
	sudo apt-get update
	sudo apt-get install owfs python-ow
	sudo nano /etc/owfs.conf
	sudo reboot
	git clone https://github.com/psamperl/HomeAutomation.git
	cd HomeAutomation/
	sudo python Sensors.py
	sudo apt-get install python-pip
	sudo pip install ubidots==1.6.6
	sudo python ubiClient.py
	sudo apt-get install curl

#GIT ADDING
	git config --global user.email <xxxxx@gmail.com>
	git config --global user.name <xxxxxx>
	git commit -a
	git push
	ls
	git add fireplace.py
	git commit -a
	git push

#Create Private.py with ubidots credentials
	ubidotstoken = 'XXXXXXX'

#HOW TO SETUP CRON
	@reboot /bin/sleep 60 && /usr/bin/curl -u <PUSHBULLET_TOKEN>: https://api.pushbullet.com/v2/pushes -d type=note -d title="Alert" -d b$

	@reboot /usr/bin/python /home/pi/HomeAutomation/kolektor.py &>/dev/null
	* * * * * /home/pi/HomeAutomation/kolektor_check.sh <PUSHBULLET_TOKEN>

	@reboot /usr/bin/python /home/pi/HomeAutomation/fireplace.py &>/dev/null
	* * * * * /home/pi/HomeAutomation/fireplace_check.sh <PUSHBULLET_TOKEN>

	@reboot /usr/bin/python /home/pi/HomeAutomation/ubiClient.py &>/dev/null
	* * * * * /home/pi/HomeAutomation/ubiClient_check.sh <PUSHBULLET_TOKEN>
