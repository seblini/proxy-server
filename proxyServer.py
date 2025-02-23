from socket import *
import sys
import select
import queue

def main():
	if len(sys.argv) <= 1:
		print('Usage : "python ProxyServer.py server_ip"\n[server_ip : It is the IP Address Of Proxy Server')
		sys.exit(2)
		
	# The proxy server is listening at 8888 
	proxy_sock = socket(AF_INET, SOCK_STREAM)
	proxy_sock.setblocking(False)
	proxy_sock.bind((sys.argv[1], 8888))
	proxy_sock.listen(100)

	# Used to mark sockets that are expecting data to
	# be sent to them
	inputs = [proxy_sock]

	# Used to mark sockets that want to send data
	outputs = []

	# Maps from a socket's memory address to a queue
	# that holds data that will later be sent
	message_queues = {}

	# Maps from a server socket's memory address to a
	# client socket's memory address
	server_mappings = {}

	# Socket registry that maps from a socket's memory
	# address to the socket itself
	sock_reg = {}

	def clean_up_sock(s):
		"""	Removes any reference to a socket from all
			collections then closes it.

		Args:
			s (socket): The socket.

		Returns:
			None
		"""
		sid = id(s)
		if s in inputs:
			inputs.remove(s)
		if s in outputs:
			outputs.remove(s)
		if sid in message_queues:
			del message_queues[sid]
		if sid in sock_reg:
			del sock_reg[sid]
		if sid in server_mappings:
			del server_mappings[sid]
		s.close()

	def handle_new_client(r, data):
		""" Creates a new server socket that will
			forward the request sent to the client
			socket.

		Args:
			r (socket): The cloent socket
			data (bytes): The request

		Returns:
			None
		"""
		# Decode the data and retrieve the headers
		msg = data.decode()
		headers = msg.split('\r\n')

		# Retrieve the path from the first header
		url_components = headers[0].split(' ')[1].split('/')

		# The hostname will be the first non-empty component
		host = url_components[1]

		# Anything after that will be the file
		file = '' if len(url_components) < 3 else '/'.join(url_components[2:])

		# Check that the hostname is valid and retrieve
		# its address
		sockaddr = None
		try:
			addrinfo = getaddrinfo(
				host=host,
				port=80,
				family=AF_INET,
				type=SOCK_STREAM
			)
			sockaddr = addrinfo[0][-1]
		except:
			pass

		# If the hostname is not valid clean up the
		# the client socket
		if not sockaddr:
			clean_up_sock(r)
			return

		# Initialize the socket and connect to the socket
		server_sock = socket(AF_INET, SOCK_STREAM)
		server_sock.setblocking(False)
		server_sock.settimeout(False)

		try:
			server_sock.connect(sockaddr)
		except:
			pass

		cid = id(r)
		sid = id(server_sock)

		# Add new server socket to the registry
		sock_reg[sid] = server_sock

		# Create a mapping from the server socket to the
		# client socket
		server_mappings[sid] = cid

		# Create an empty queue to hold requests that will
		# be sent by the server socket
		message_queues[sid] = queue.Queue()

		# Add the server socket to the inputs list to notify
		# select that we are expecting a response
		inputs.append(server_sock)

		# Modify the request to use the true hostname and path
		request = (
				f'GET /{file} HTTP/1.1\r\n'
				f'Host: {host}\r\n'
				f'Connection: close\r\n'
				'\r\n'
				).encode()

		# Add the request to the server socket's message queue
		message_queues[sid].put(request)

		# Add the server socket to the outputs list to notify
		# select that we want to send a request
		if server_sock not in outputs:
			outputs.append(server_sock)

	def forward_response(s, data):
		""" Forwards data sent to a server socket
			to its corresponding client socket.

		Args:
			s (socket): The server socket
			data (bytes): The data

		Returns:
			None
		"""
		try:
			# Retrieve the server socket's corresponding
			# client socket
			cid = server_mappings[id(s)]

			# Add the data to the client socket's message
			# queue
			message_queues[cid].put(data)

			# Add the client socket to the outputs list to
			# notify select that we want to send the data
			if cid not in outputs:
				outputs.append(sock_reg[cid])
		except KeyError:
			clean_up_sock(s)

	while inputs:
		# Call select to retrieve the sockets that are ready to be used
		readable, writable, exceptional = select.select(inputs, outputs, inputs)

		# Handle all socket that are ready to be read from
		for r in readable:
			# If a request is sent to the proxy socket, it is
			# a new client looking to connect
			if r is proxy_sock:
				# Accept the connection as a new client socket
				client_sock, addr = proxy_sock.accept()
				client_sock.setblocking(False)
				
				cid = id(client_sock)

				# Add the client socket to the registry
				sock_reg[cid] = client_sock

				# Add the client socket to the inputs list to
				# notify select that we are expecting a request
				inputs.append(client_sock)

				# Create an empty queue to hold responses that
				# will sent by the client socket
				message_queues[cid] = queue.Queue()
				continue

			try:
				# Read the incoming data from the socket
				data = r.recv(4096)
			except (BrokenPipeError, ConnectionResetError):
				clean_up_sock(r)
				continue

			# If the there is no data we close the connection
			if not data:
				clean_up_sock(r)
				continue

			# If we are receiving data to a server socket we
			# must forward it to the corresponding client socket
			if id(r) in server_mappings:
				forward_response(r, data)
				continue

			handle_new_client(r, data)

		# Handle all sockets that are ready to be written to
		for w in writable:
			try:
				# Retrieve the data to be sent from the socket's message queue
				msg = message_queues[id(w)].get_nowait()

				# Send the data
				w.send(msg)
			except queue.Empty:
				outputs.remove(w)
			except:
				clean_up_sock(w)
		
		# Handle all exceptional sockets
		for e in exceptional:
			# Any sockets that fall into this category will be closed
			clean_up_sock(e)	

		'''
		## filetouse = ## FILL IN HERE...

		try:
			# Check wether the file exist in the cache

			## FILL IN HERE...

			fileExist = "true"
			# ProxyServer finds a cache hit and generates a response message
			client.send("HTTP/1.0 200 OK\r\n")            
			client.send("Content-Type:text/html\r\n")


			## FILL IN HERE...

		# Error handling for file not found in cache, need to talk to origin server and get the file
		except IOError:
			if fileExist == "false": 

				## FILL IN HERE...
				## except:
					print("Illegal request")                                               
			else:
				# HTTP response message for file not found
				client.send("HTTP/1.0 404 sendErrorErrorError\r\n")                             
				client.send("Content-Type:text/html\r\n")
				client.send("\r\n")

		# Close the client and the server sockets    
		client.close() 
		'''
	server.close()

if __name__ == '__main__':
	main()
