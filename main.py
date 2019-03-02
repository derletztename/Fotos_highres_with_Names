#!/usr/bin/env python
'''Fotos_highres_with_Names.
Take a photo using a USB or Raspberry Pi camera.
'''

import os
import time
import json
import requests
import numpy as np
import cv2
import sys
from farmware_tools import device, app

try:
    points =  app.get_plants()         #Get all points from webapp, would be smarter to get plants, will try that later
    position_x = int(round(device.get_current_position('x')))      #Actual X-Position
    position_y = int(round(device.get_current_position('y')))      #Actual Y-Position
    all_plants = []
except KeyError:
     log("Loading points/positions failed","error")


def farmware_api_url():

    major_version = int(os.getenv('FARMBOT_OS_VERSION', '0.0.0')[0])
    base_url = os.environ['FARMWARE_URL']
    return base_url + 'api/v1/' if major_version > 5 else base_url

def log(message, message_type):
    'Send a message to the log.'
    try:
        os.environ['FARMWARE_URL']
    except KeyError:
        print(message)
    else:
        log_message = '[take-photo] ' + str(message)
        headers = {
            'Authorization': 'bearer {}'.format(os.environ['FARMWARE_TOKEN']),
            'content-type': "application/json"}
        payload = json.dumps(
            {"kind": "send_message",
             "args": {"message": log_message, "message_type": message_type}})
        requests.post(farmware_api_url() + 'celery_script',
                      data=payload, headers=headers)

def rotate(image):
    'Rotate image if calibration data exists.'
    angle = float(os.environ['CAMERA_CALIBRATION_total_rotation_angle'])
    sign = -1 if angle < 0 else 1
    turns, remainder = -int(angle / 90.), abs(angle) % 90  # 165 --> -1, 75
    if remainder > 45: turns -= 1 * sign  # 75 --> -1 more turn (-2 turns total)
    angle += 90 * turns                   #        -15 degrees
    image = np.rot90(image, k=turns)
    height, width, _ = image.shape
    matrix = cv2.getRotationMatrix2D((int(width / 2), int(height / 2)), angle, 1)
    return cv2.warpAffine(image, matrix, (width, height))

def search_plant():
         'Comparing axis positions with plant points to determine where we are.'
         i=0
#         app_points = json.loads(points)
         for plant_points in points:                        #Loop through all positons (plants, tools, etc)
                all_plants.append({                         #Set up an array where every item is one plant
                        'name': plant_points[u'name'],
                        'x': plant_points[u'x'],
                        'y': plant_points[u'y']})
                if all_plants[i]['x'] == position_x and all_plants[i]['y'] == position_y:   #See if current position matches with the plant
                        current_plant_name = json.dumps(plant_points[u'name']).strip('""')      #Extract plant name and erase quotes
                        return current_plant_name                                               #Get the plant_name out of the function
                        break                                                                   #Stop looping when the plant name was found
                else:
                        i=i + 1                                                                 #Add 1 to loop count


def image_filename():
    'Prepare filename with timestamp.'
    plant_name = search_plant()             #Get the plant name from its function
    if plant_name != None:
        epoch = str(time.strftime("%d_%m_%Y"))  #Changed the timestamp from unix to "DD_MM_YYYY"
        filename = '{}_x{}_y{}_{}.jpg'.format(plant_name, position_x, position_y,epoch)     #Add plant_name, x-and y-positions and timestamp
        return filename
    else:
        log("No plant found. Make sure we are right on top of a registered plant.","error")
        print("error")
        log(all_plants,"info")
        log("{} Plants detected.".format(len(all_plants)),"info")
        sys.exit(2)



def upload_path(filename):
    'Filename with path for uploading an image.'
    try:
        images_dir = '/images'
            #os.environ['IMAGES_DIR']
    except KeyError:
        images_dir = '/tmp/images'
    path = images_dir + os.sep + filename
    return path

def usb_camera_photo():
    'Take a photo using a USB camera.'
    # Settings
    camera_port = 0      # default USB camera port
    discard_frames = 20  # number of frames to discard for auto-adjust

    # Check for camera
    
    filename = image_filename()
    if not os.path.exists('/dev/video' + str(camera_port)):
        print("No camera detected at video{}.".format(camera_port))
        camera_port += 1
        print("Trying video{}...".format(camera_port))
        if not os.path.exists('/dev/video' + str(camera_port)):
            print("No camera detected at video{}.".format(camera_port))
            log("USB Camera not detected.", "error")

    # Open the camera
    camera = cv2.VideoCapture(camera_port)
    time.sleep(0.1)

    # Let camera adjust
    for _ in range(discard_frames):
        camera.grab()

    # Take a photo
    ret, image = camera.read()

    # Close the camera
    camera.release()

    # Output
    if ret:  # an image has been returned by the camera
        ###
        # Try to rotate the image
        try:
            final_image = rotate(image)
        except:
            final_image = image
        else:
            filename = 'rotated_' + filename
        # Save the image to file
        cv2.imwrite(upload_path(filename), final_image)
        print("Image saved: {}".format(upload_path(filename)))
    else:  # no image has been returned by the camera
        log("Problem getting image.", "error")

def rpi_camera_photo():
    'Take a photo using the Raspberry Pi Camera.'
    from subprocess import call
    try:
        filename_path = upload_path(image_filename())
        retcode = call(
            ["raspistill", "-w", "3280", "-h", "2464", "-o", filename_path])
        if retcode == 0:
            print("Image saved: {}".format(filename_path))
        else:
            log("Problem getting image.", "error")
    except OSError:
        log("Raspberry Pi Camera not detected.", "error")

if __name__ == '__main__':
    try:
        CAMERA = os.environ['camera']
    except (KeyError, ValueError):
        CAMERA = 'USB'  # default camera

    if 'RPI' in CAMERA:
        rpi_camera_photo()
    else:
        usb_camera_photo()
