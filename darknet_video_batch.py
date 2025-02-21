from ctypes import *
import math
import random
import os
import cv2
import numpy as np
import time
import darknet
import argparse
import glob
import operator

# !python darknet_video -v -c -w 
# augument parser
ap = argparse.ArgumentParser()
ap.add_argument("-v" ,"--video", type=str, required=True, 
                help="Path to input video folder")
ap.add_argument("-c","--config", default="./config.json",
               help="Path to yolo config file")
ap.add_argument("-w","--weights",type=str, required=True,
                help="Path to yolo weight")
ap.add_argument("-l","--label",type=str, default="./data/classes.names",
                help="Path to label file")
ap.add_argument("-m","--meta",type=str, default="./data/yolov4.data",
                help="Path to metaPath")

args = vars(ap.parse_args())

def check_argument(args):
    assert os.path.isdir(args["video"]) == True, "Can't find " + args["video"]
    assert os.path.isfile(args["config"]) == True, "Can't find " + args["config"]
    assert os.path.isfile(args["weights"]) == True, "Can't find " + args["weights"]
    assert os.path.isfile(args["meta"]) == True, "Can't find " + args["meta"]
    assert os.path.isfile(args["label"]) == True, "Can't find " + args["label"]

def convertBack(x, y, w, h):
    xmin = int(round(x - (w / 2)))
    xmax = int(round(x + (w / 2)))
    ymin = int(round(y - (h / 2)))
    ymax = int(round(y + (h / 2)))
    return xmin, ymin, xmax, ymax


def cvDrawBoxes(detections, img):
    for detection in detections:
        x, y, w, h = detection[2][0],\
            detection[2][1],\
            detection[2][2],\
            detection[2][3]
        xmin, ymin, xmax, ymax = convertBack(
            float(x), float(y), float(w), float(h))
        pt1 = (xmin, ymin)
        pt2 = (xmax, ymax)
        color = [int(c) for c in COLORS[LABELS.index(detection[0].decode())]]
        #print(color, type(color))
        cv2.rectangle(img, pt1, pt2, color, 1)
        cv2.putText(img,
                    detection[0].decode() +
                    " [" + str(round(detection[1] * 100, 2)) + "]",
                    (pt1[0], pt1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    color, 2)
    return img


netMain = None
metaMain = None
altNames = None


def YOLO():


    global metaMain, netMain, altNames, COLORS, LABELS
    
    videoPath = args["video"]
    configPath = args["config"]
    weightPath = args["weights"]
    metaPath = args["meta"]
    labelsPath = args["label"]
    
    check_argument(args)
    
    LABELS = open(labelsPath).read().strip().split("\n")
    #print(LABELS, len(LABELS))
    np.random.seed(42)
    COLORS = np.random.randint(0, 255, size=(len(LABELS), 3), dtype="uint8")
    
    if not os.path.exists(configPath):
        raise ValueError("Invalid config path `" +
                         os.path.abspath(configPath)+"`")
    if not os.path.exists(weightPath):
        raise ValueError("Invalid weight path `" +
                         os.path.abspath(weightPath)+"`")
    if not os.path.exists(metaPath):
        raise ValueError("Invalid data file path `" +
                         os.path.abspath(metaPath)+"`")
    if netMain is None:
        netMain = darknet.load_net_custom(configPath.encode(
            "ascii"), weightPath.encode("ascii"), 0, 1)  # batch size = 1
    if metaMain is None:
        metaMain = darknet.load_meta(metaPath.encode("ascii"))
    if altNames is None:
        try:
            with open(metaPath) as metaFH:
                metaContents = metaFH.read()
                import re
                match = re.search("names *= *(.*)$", metaContents,
                                  re.IGNORECASE | re.MULTILINE)
                if match:
                    result = match.group(1)
                else:
                    result = None
                try:
                    if os.path.exists(result):
                        with open(result) as namesFH:
                            namesList = namesFH.read().strip().split("\n")
                            altNames = [x.strip() for x in namesList]
                except TypeError:
                    pass
        except Exception:
            pass
    
    video_list =  glob.glob(videoPath+'/*')
    correct_pred = 0
    
    for i,vid in enumerate(video_list):
      cap = cv2.VideoCapture(vid)
      cap.set(3, 1280)
      cap.set(4, 720)

      # Create an image we reuse for each detect
      darknet_image = darknet.make_image(darknet.network_width(netMain),
                                      darknet.network_height(netMain),3)

      res = dict()                                
      while True:
          prev_time = time.time()
          ret, frame_read = cap.read()

          if not ret:
            break

          frame_rgb = cv2.cvtColor(frame_read, cv2.COLOR_BGR2RGB)
          frame_resized = cv2.resize(frame_rgb,
                                    (darknet.network_width(netMain),
                                      darknet.network_height(netMain)),
                                    interpolation=cv2.INTER_LINEAR)

          darknet.copy_image_from_bytes(darknet_image,frame_resized.tobytes())

          detections = darknet.detect_image(netMain, metaMain, darknet_image, thresh=0.25)
          if detections:
            if detections[0][0] in res:
              if(detections[0][1] > res[detections[0][0]]):
                res[detections[0][0]] = detections[0][1]
            else:
              res[detections[0][0]] = detections[0][1]
          image = cvDrawBoxes(detections, frame_resized)
          image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
          cv2.waitKey(3)
      cap.release()
      print('%03d/%03d: %s is predicted to class %s' % (i+1, len(video_list), vid, res))
      if res:
        if(vid.split('/')[-1].split('_')[1]==max(res.items(), key=operator.itemgetter(1))[0].decode('utf-8')):
          correct_pred += 1
    print('Correct Prediction: %s/%s' % (correct_pred,len(video_list)))

if __name__ == "__main__":
    YOLO()
