
import cv2
import numpy as np
import sys
import os
import copy
from errno import errorcode
from PIL import Image







def flipImage(img):
    height, width, channels = img.shape
    flip = np.zeros((height, width, 3), np.uint8    )
    ### MISE
        # Fill flip with pixels from img to flip the img!
    return flip






try:
    sys.argv[1]
    sys.argv[2]
except:
    print errorcode[99]
    sys.exit(99)

file_path = sys.argv[1]
file_name = sys.argv[1]
print file_path
print    file_name
if not os.path.exists(file_path):
    print 'Path not existing'
    print errorcode[2]
    sys.exit(2)

try:
    Image.open(file_name)
except:
    print errorcode[3]
    sys.exit(3)

img = cv2.imread(sys.argv[1], 1)

dir = sys.argv[2]
if not os.path.exists(dir):
    os.makedirs(dir)

reg = img
flip = flipImage(img)
doub = np.concatenate((img,flip),1)

cv2.imwrite(os.path.join(dir , 'regular.jpg'), reg)
cv2.imwrite(os.path.join(dir , 'flip.jpg'), flip)
cv2.imwrite(os.path.join(dir , 'side-by-side.jpg'), doub)
