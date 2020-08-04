import cv2
import socket
import time
import numpy as np
import threading
from inputs import get_gamepad
HOST = '192.168.1.2'
PORT = 2070

########################
#This is the control-computer side script
########################

#this is a separate thread for getting gamepad events and sending controls over the socket
def control_send(tx_conn):
	power = 0
	steering = 0
	last_rz = 0
	last_z = 0
	while True:
		#grab gamepad events
		events = get_gamepad()
		for event in events:
			if event.code == "ABS_RX": #right joystick
				if abs(event.state - 128) > 10:
					steering = event.state - 128
				else:
					steering = 0
			elif event.code == "ABS_RZ": #left trigger
				last_rz = event.state
			elif event.code == "ABS_Z": #right trigger
				last_z = event.state

			#if both triggers are above or below the threshold, no power to motors
			if last_rz > 10 and last_z < 10:
				power = last_rz / 2
			elif last_z > 10 and last_rz < 10:
				power = -last_z / 2
			elif last_z > 10 and last_rz > 10:
				power = 0
			elif last_z < 10 and last_rz < 10:
				power = 0
		print("Power: " + str(power) + "Steering: " + str(steering))
		#send transmissions
		data = np.array([steering, power], np.int8)
		tx_conn.sendall(data.tobytes())

#wait for car to connect
#TODO: the car should be the server ideally, with a static DHCP allocation
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((HOST, PORT))
sock.listen(1)
print('Waiting for connection')

conn, addr = sock.accept()
print('connected to:')
print(addr)

#start controls thread
control_thread = threading.Thread(target=control_send, args=(conn,))
control_thread.start()

while True:
	#the first two bytes of the transmission are the length of the image to follow
	HEADER_LEN = 2
	bytes_received = 0
	header = b''
	while bytes_received < HEADER_LEN:
		data = conn.recv(HEADER_LEN - bytes_received)
		bytes_received += len(data)
		if len(data) == 0:
			exit()
		header += data

	#reconstruct length from high and low bytes
	head_int = np.frombuffer(header, np.uint8)
	pic_length = head_int[0] * 256 + head_int[1]

#	print('Receiving frame of size: ' + str(pic_length))
	picture = b''
	bytes_received = 0
	while bytes_received < pic_length:
		data = conn.recv(min(pic_length - bytes_received, 4096))
		bytes_received += len(data)
#		print('Chunk of size: ' + str(len(data)))
		if len(data) == 0:
			exit()
		picture += data

	#we have the full picture
#	print('receive done')
	arr_pic = np.frombuffer(picture, np.uint8)
	#print(arr_pic)
	frame = cv2.imdecode(arr_pic, cv2.IMREAD_COLOR)
	cv2.imshow('frame', frame)
	cv2.waitKey(1)

control_thread.join()
