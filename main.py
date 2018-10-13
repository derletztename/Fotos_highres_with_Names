"""Fotos_highres_with_Names"""

from farmware_tools import device
from farmware_tools import app
import os, sys, time, subprocesspoints = app.get('points')
position_x = device.get_current_position('x')
position_y = device.get_current_position('y')filename = '{}/{}.jpg'.format(os.environ['IMAGES_DIR'], int(time.time()))
ret = subprocess.call(['raspistill', '-w', '1024', '-h', '768', '-o', filename])
if ret != 0:
   device.log('Problem getting image (error code: {}).'.format(ret), 'error')
   sys.exit(1)
