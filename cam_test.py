import cv2
import time
import socket
import numpy as np
import threading
import pigpio
HOST = '192.168.1.2'
PORT = 2070

def control_recv(rx_conn):
	MOTOR_F = 17
	MOTOR_R = 22
	SERVO = 27
	MEDIAN = 1500
	pi = pigpio.pi()

	while True:
		#wait for transmission of data length
		CONTROL_LEN = 2
		bytes_received = 0
		control = b''
		while bytes_received < CONTROL_LEN:
			data = rx_conn.recv(CONTROL_LEN - bytes_received)
			bytes_received += len(data)
			if len(data) == 0:
                		exit()
			control += data

		control_arr = np.frombuffer(control, np.int8)

		#act upon controls
		print("Steering: ", control_arr[0])
		print("Power: ", control_arr[1])
		pi.set_servo_pulsewidth(SERVO, MEDIAN + (control_arr[0] * 3))
		if control_arr[1] > 0:
			pi.set_PWM_dutycycle(MOTOR_R, 0)
			pi.set_PWM_dutycycle(MOTOR_F, control_arr[1] * 2)
		else:
			pi.set_PWM_dutycycle(MOTOR_F, 0)
			pi.set_PWM_dutycycle(MOTOR_R, -control_arr[1] * 2)


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#blocking
sock.connect((HOST, PORT))

control_thread = threading.Thread(target=control_recv, args=(sock,))

control_thread.start()

#open camera
cap = cv2.VideoCapture(0)

print("start reading")

while True:
	ret, frame = cap.read()
	small_frame = cv2.resize(frame, (640, 480))
	ret, data = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
	length = len(data)
	if length > 60000:
		print('skipping! ' + str(length))
		continue
	high_bits, low_bits = divmod(length, 256)
	data = np.insert(data, 0, [high_bits, low_bits])
	print('Sending frame of size: ' + str(length) + ' bytes')
	sock.sendall(data.tobytes())

control_thread.join()
