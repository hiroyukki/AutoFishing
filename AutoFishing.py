import sys
import os
import threading
import time
import logging
import random
import cv2
import numpy as np
import pyautogui

def screenshot():
    img = pyautogui.screenshot()
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def imageDiff(img1, img2):
    diff = cv2.absdiff(img1, img2)
    _, diff = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    return cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

# get contour with largest area, that maybe buoy contour if there is no interference
def maxContour(img):
    contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    maxContourIdx = -1
    maxContourArea = 0
    for i in range(len(contours)):
        area = cv2.contourArea(contours[i])
        if area > maxContourArea:
            maxContourArea = area
            maxContourIdx = i
    if maxContourIdx != -1:
        return contours[maxContourIdx]
    return None

def getCentroid(contour):
    try:
        moment = cv2.moments(contour, False)
        if moment['m00'] != 0:
            return int(moment['m10'] / moment['m00']), int(moment['m01'] / moment['m00'])
    except:
        pass
    return 0, 0

# find position of buoy, return position and image at that time on successful
def findBuoyPosition(initImg, timeout):
    for i in range(timeout):
        time.sleep(1)
        curImg = screenshot()
        # difference of inital image and current image is buoy
        diff = imageDiff(initImg, curImg)
        try:
            contour = maxContour(diff)
            if cv2.contourArea(contour) > 300:
                # Contour of buoy is irregular, assume that centroid position is the buoy position
                x, y = getCentroid(contour)
                if x != 0:
                    return x, y, curImg
        except:
            pass

    logger.warn('buoy not found')
    return 0, 0, None

def waitForBite(initImg, timeout, x, y, width, height):
    beginTime = time.time()
    prevImg = initImg
    exceptCount = 1
    while True:
        lastTime = time.time() - beginTime
        if lastTime > timeout:
            return 2
        # pyautogui.moveTo((1 - lastTime / timeout) * width, height - 10, 0)
        time.sleep(0.1)
        curImg = screenshot()
        # check change around the buoy
        y0 = y - 100 if y - 100 >= 0 else 0
        x0 = x - 100 if x - 100 >= 0 else 0
        y1 = y + 100 if y + 100 <= height else height
        x1 = x + 100 if x + 100 <= width else width
        diff = imageDiff(prevImg[y0:y1, x0:x1], curImg[y0:y1, x0:x1])
        prevImg = curImg
        try:
            contour = maxContour(diff)
            area = cv2.contourArea(contour)
            # print(area)
            if area > 800 + y * 3:
                # print(cv2.contourArea(contour))
                # cv2.imwrite('diff.jpg', diff)
                # cv2.imwrite('prev.jpg', prevImg[y0:y1, x0:x1])
                # cv2.imwrite('cur.jpg', curImg[y0:y1, x0:x1])
                return 0
        except Exception as e:
            # print(e)
            exceptCount = exceptCount + 1
            if exceptCount > 2:
                return 3

def fishingLoop(key, width, height):
    logger.info('begin fishing loop')
    initImg = screenshot()
    time.sleep(0.2)
    pyautogui.press(key)
    time.sleep(1)
    pyautogui.moveTo(50, 50, 0)
    x, y, buoyImg = findBuoyPosition(initImg, 8)
    if x == 0:
        return 1
    logger.info('buoy found at position ({}, {})'.format(x, y))
    pyautogui.moveTo(100, 100, 0)
    waitResult = waitForBite(buoyImg, 20, x, y, width, height)
    if waitResult == 0:
        # move to buoy and right click
        time.sleep(0.1)
        logger.info('bite! right click ({}, {})'.format(x, y))
        pyautogui.moveTo(x, y, 0)
        pyautogui.rightClick()
        time.sleep(1) # wait for fish load into pack
        pyautogui.moveTo(150, 150, 0)
    else:
        logger.error('waitForBite returned: {}'.format(waitResult))

    return waitResult

def autoFishing():
    pyautogui.FAILSAFE = False

    while True:
        width, height = pyautogui.size()
        try:
            pyautogui.press(destroyKey)
            fishingLoop(fishingKey, width, height)
            # Make your character jump randomly to resist cheating detection
            if random.randint(1,100) < 8:
                pyautogui.press('space')
            time.sleep(1)
        except Exception as e:
            logger.error(repr(e))
            time.sleep(1)

destroyKey = 'r' # destroy bad fishes
fishingKey = 'f' # replace to your fishing key
logger = logging.getLogger('auto_fishing')
timeoutMinutes = random.randint(90, 110) # close wow on timeout

def exitWorker():
    logger.info("close wow after {} minutes".format(timeoutMinutes))
    time.sleep(timeoutMinutes * 60)
    logger.info("close wow")
    # pyautogui.press('r')
    time.sleep(20)
    pyautogui.hotkey('alt', 'f4')
    os._exit(1)

def main(autoClose):
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s %(message)s'))
    logger.addHandler(handler)
    closeThread = threading.Thread(target=exitWorker)
    if autoClose:
        closeThread.start()
    try:
        autoFishing()
    except BaseException as e:
        logger.error(repr(e))
    finally:
        os._exit(1)

if __name__ == '__main__':
    autoClose = False
    if len(sys.argv) == 2 and sys.argv[1] == 'autoClose':
        autoClose = True
    main(autoClose) 