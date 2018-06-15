import serial
import struct
import time
import cv2
import threading
from flask import Flask, render_template, Response, request

arduino = serial.Serial('/dev/ttyACM0', 115200, timeout=.1)

movement_detected = False
distance = 0
ard_servo_pos = 190
set_servo_pos = 50
keep_alive = True

time.sleep(2)
arduino.write(b'a')
arduino.flush()

keep_alive = True

def stop():
    global keep_alive
    print('Setting keep alive to false')
    keep_alive = False

class VideoCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0)
    
    def __del__(self):
        self.video.release()
    
    def get_frame(self):
        global distance
        success, image = self.video.read()
        cv2.putText(image, str(distance), (20, 400), cv2.FONT_HERSHEY_PLAIN, 4, (255, 255, 255))
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()

class ClientThread(threading.Thread):
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
                    # print(data)
                    if not self.waiting_for_dist and not self.waiting_for_pos:
                        self.handle_command(data)
                    elif self.waiting_for_dist:
                        distance = data
                        print(data)
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
    print(request.data)
    json = request.get_json()
    print(json)
    set_servo_pos = json['pos']
    return 'success'

try:
    client_thread = ClientThread()
    client_thread.start()

    app.run(host='0.0.0.0', debug=True)
except KeyboardInterrupt:
    stop()
    client_thread.join()

