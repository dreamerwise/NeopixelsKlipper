# NeopixelsKlipper
BLV mgn cube style of neopixel rings for klipper


CONFIG:

monitoring.cfg contains confuguration like basic color sellection, order of rings and offsets for first led and GPIO pin in usage

SETUP

You'll need to install the Adafruit_Blinka library that provides the CircuitPython support in Python. This may also require verifying you are running Python 3. 
Since each platform is a little different, and Linux changes often, please visit the CircuitPython on Linux guide to get your computer ready!
Once that's done, from your command line run the following command: 

sudo pip3 install rpi_ws281x adafruit-circuitpython-neopixel sudo python3 -m pip install --force-reinstall adafruit-blinka

If your default Python is version 3 you may need to run 'pip' instead. Just make sure you aren't trying to use CircuitPython on Python 2.x, it isn't supported!

SETTING UP SCRIPT AND SERVICE:

Copy “klipper_monitor.service” to /etc/systemd/system/
Copy “monitoring.py” and "monitoring.cfg" to /home/pi/neopixels/ (you need to create neopixels directory)

When files will be set up on rpi run commands:

systemctl enable klipper_monitor

systemctl start klipper_monitor


HARDWARE SETUP is described in connection_diag.jpg
