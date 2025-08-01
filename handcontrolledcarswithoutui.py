import cv2
from cvzone.HandTrackingModule import HandDetector
import math
import numpy as np
import RPi.GPIO as GPIO
import time

# ===== GPIO SETUP =====
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

motor_pins = {"IN1": 17, "IN2": 18, "IN3": 22, "IN4": 23}
for pin in motor_pins.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

ENA = 12
ENB = 13
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)

pwm_left = GPIO.PWM(ENA, 1000)
pwm_right = GPIO.PWM(ENB, 1000)

BASE_LEFT_SPEED = 65
BASE_RIGHT_SPEED = 55
TURN_LEFT_SPEED = 100
TURN_RIGHT_SPEED = 100

pwm_left.start(0)
pwm_right.start(0)

current_command = "STOPPED"

def set_motor_state(in1, in2, in3, in4):
    GPIO.output(motor_pins["IN1"], in1)
    GPIO.output(motor_pins["IN2"], in2)
    GPIO.output(motor_pins["IN3"], in3)
    GPIO.output(motor_pins["IN4"], in4)

def move_forward():
    global current_command
    current_command = "FORWARD"
    print(current_command)
    set_motor_state(0, 1, 0, 1)
    pwm_left.ChangeDutyCycle(BASE_LEFT_SPEED)
    pwm_right.ChangeDutyCycle(BASE_RIGHT_SPEED)

def move_backward():
    global current_command
    current_command = "BACKWARD"
    print(current_command)
    set_motor_state(1, 0, 1, 0)
    pwm_left.ChangeDutyCycle(BASE_LEFT_SPEED)
    pwm_right.ChangeDutyCycle(BASE_RIGHT_SPEED)

def move_left():
    global current_command
    current_command = "LEFT"
    print(current_command)
    set_motor_state(1, 0, 0, 1)
    pwm_left.ChangeDutyCycle(TURN_LEFT_SPEED)
    pwm_right.ChangeDutyCycle(TURN_LEFT_SPEED)

def move_right():
    global current_command
    current_command = "RIGHT"
    print(current_command)
    set_motor_state(0, 1, 1, 0)
    pwm_left.ChangeDutyCycle(TURN_RIGHT_SPEED)
    pwm_right.ChangeDutyCycle(TURN_RIGHT_SPEED)

def stop():
    global current_command
    current_command = "STOPPED"
    print(current_command)
    set_motor_state(0, 0, 0, 0)
    pwm_left.ChangeDutyCycle(0)
    pwm_right.ChangeDutyCycle(0)

# ===== Camera and Hand Detector =====
FRAME_WIDTH = 320
FRAME_HEIGHT = 240
cap = cv2.VideoCapture(0)
cap.set(3, FRAME_WIDTH)
cap.set(4, FRAME_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, 25)

detector = HandDetector(detectionCon=0.5, maxHands=1)

x_vals = [300, 245, 200, 170, 145, 130, 112, 103, 93, 87, 80, 75, 70, 67, 62, 59, 57]
y_vals = [20,  25,  30,  35,  40,  45,  50,  55,  60, 65,  70, 75, 80, 85, 90, 95, 100]
coff = np.polyfit(x_vals, y_vals, 2)

CENTER_TOL = 0.6
LEFT_ZONE = FRAME_WIDTH * (1 - CENTER_TOL) / 2
RIGHT_ZONE = FRAME_WIDTH - LEFT_ZONE

TARGET_DIST = 90
MIN_DIST = 80
MAX_DIST = 120

frame_count = 0

# ===== Main Loop =====
try:
    while True:
        success, img = cap.read()
        if not success:
            stop()
            continue

        frame_count += 1
        if frame_count % 2 != 0:
            continue

        img = cv2.flip(img, 1)
        hands, _ = detector.findHands(img, draw=False)

        if hands:
            hand = hands[0]
            lmList = hand['lmList']
            x, y, w, h = hand['bbox']
            x1, y1 = lmList[5][:2]
            x2, y2 = lmList[17][:2]

            pixel_dist = int(math.hypot(x2 - x1, y2 - y1))
            A, B, C = coff
            dist_cm = A * pixel_dist ** 2 + B * pixel_dist + C
            dist_cm = max(20, min(MAX_DIST, dist_cm))

            hand_center_x = x + w // 2
            moved = False

            if hand_center_x < LEFT_ZONE:
                move_left()
                moved = True
            elif hand_center_x > RIGHT_ZONE:
                move_right()
                moved = True
            else:
                if dist_cm > TARGET_DIST + 10:
                    move_forward()
                    moved = True
                elif dist_cm < MIN_DIST:
                    move_backward()
                    moved = True

            if not moved:
                stop()
        else:
            print("No hand detected")
            stop()

        time.sleep(0.05)

except KeyboardInterrupt:
    print("Interrupted by user")
finally:
    stop()
    pwm_left.stop()
    pwm_right.stop()
    cap.release()
    GPIO.cleanup()
