import serial
import struct
import time
import cv2
import threading
from flask import Flask, render_template, Response, request

arduino = serial.Serial('/dev/ttyACM0', 115200, timeout=.1)

faceCascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

movement_detected = False
distance = 0
ard_servo_pos = 190
set_servo_pos = 90
keep_alive = True
image = None
faces = None

cam_id = 1

time.sleep(2)
arduino.write(b'a')
arduino.flush()

def stop():
    global keep_alive
    print('Setting keep alive to false')
    keep_alive = False

class VideoCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(cam_id)
    
    def __del__(self):
        self.video.release()
    
    def get_frame(self):
        global distance
        global image
        global faces
        success, image = self.video.read()
        cv2.putText(image, str(distance), (20, 400), cv2.FONT_HERSHEY_PLAIN, 4, (255, 255, 255))
        if faces is not None:
            for (x, y, w, h) in faces:
                cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()

class FaceDetectionThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global keep_alive
        global image
        global faces

        while keep_alive:
            if image is not None:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                faces = faceCascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )


class SerialCommThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.waiting_for_dist = False
        self.waiting_for_pos = False
    
    def handle_command(self, data):
        global movement_detected
        global set_servo_pos

        if data & 1: # receive distance from arduino
            self.waiting_for_dist = True
        elif data & 2: # arduino detected movement, alert
            movement_detected = True
        elif data & 4: # arduino is about to send its servo position
            self.waiting_for_pos = True
        elif data & 8: # arduino is waiting for position command
            string = struct.pack('!B', set_servo_pos)
            arduino.write(string)
            arduino.flush()

    def run(self):
        global keep_alive
        global arduino
        global distance
        global ard_servo_pos

        while keep_alive:
            try:
                data = arduino.read()
                if data:
                    data = ord(data)
                    if not self.waiting_for_dist and not self.waiting_for_pos:
                        self.handle_command(data)
                    elif self.waiting_for_dist:
                        distance = data
                        self.waiting_for_dist = False
                    elif self.waiting_for_pos:
                        ard_servo_pos = data
                        self.waiting_for_pos = False
            except:
                break

app = Flask(__name__)

@app.route('/')
def index():
    global set_servo_pos
    return render_template('index.html', pos=set_servo_pos)

def gen(camera):
    while True:
        frame = camera.get_frame()
        yield(b'--frame\r\n'
              b'Content-Type: image\jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video-feed')
def video_feed():
    return Response(gen(VideoCamera()),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/set-pos', methods=['PUT'])
def set_pos():
    global set_servo_pos
    json = request.get_json()
    set_servo_pos = json['pos']
    return 'success'

try:
    face_detection_thread = FaceDetectionThread()
    face_detection_thread.start()
    serial_comm_thread = SerialCommThread()
    serial_comm_thread.start()

    app.run(host='0.0.0.0', debug=True)
except KeyboardInterrupt:
    stop()
    serial_comm_thread.join()
    face_detection_thread.join()
