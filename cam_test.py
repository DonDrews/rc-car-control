import cv2
import time
import socket
import numpy as np
import threading
import pigpio
HOST = '192.168.1.2'
PORT = 2070

########################
#This is the OBC side script
########################

#this is run in a separate thread from the video stream
def control_recv(rx_conn):
	#pin numbers of the connections to the power board
	MOTOR_F = 17
	MOTOR_R = 22
	SERVO = 27
	#this is the servo pulse width for driving straight
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

		#act upon controls by setting pulse widths
		print("Steering: ", control_arr[0])
		print("Power: ", control_arr[1])
		pi.set_servo_pulsewidth(SERVO, MEDIAN + (control_arr[0] * 3))

		#ensure that only one side of the H-bridge is active at each moment
		if control_arr[1] > 0:
			pi.set_PWM_dutycycle(MOTOR_R, 0)
			pi.set_PWM_dutycycle(MOTOR_F, control_arr[1] * 2)
		else:
			pi.set_PWM_dutycycle(MOTOR_F, 0)
			pi.set_PWM_dutycycle(MOTOR_R, -control_arr[1] * 2)


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#blocking
sock.connect((HOST, PORT))

#start controls thread
control_thread = threading.Thread(target=control_recv, args=(sock,))
control_thread.start()

#open camera
cap = cv2.VideoCapture(0)

print("start reading")

while True:
	#read a frame and resize to 480p
	ret, frame = cap.read()
	small_frame = cv2.resize(frame, (640, 480))

	#low quality jpeg encoding for low-bandwidth wireless connection
	ret, data = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
	length = len(data)
	#TODO: it seems that on some runs, all the images are 100kB+, while on most they
	# are <10kB. Unsure why this happens.
	if length > 60000:
		print('skipping! ' + str(length))
		continue
	#put length of image as first two bytes in data stream
	high_bits, low_bits = divmod(length, 256)
	data = np.insert(data, 0, [high_bits, low_bits])
	print('Sending frame of size: ' + str(length) + ' bytes')
	sock.sendall(data.tobytes())

control_thread.join()
