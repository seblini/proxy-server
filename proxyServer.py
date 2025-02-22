from socket import *
import sys
import select
import queue
import ssl

def main():
	if len(sys.argv) <= 1:
		print('Usage : "python ProxyServer.py server_ip"\n[server_ip : It is the IP Address Of Proxy Server')
		sys.exit(2)
		
	# The proxy server is listening at 8888 
	server = socket(AF_INET, SOCK_STREAM)
	server.setblocking(False)
	server.bind((sys.argv[1], 8888))
	server.listen(100)

	inputs = [server]
	outputs = []
	message_queues = {}
	client_mappings = {}

	# context = ssl.create_default_context()

	def clean_up_sock(s):
		if s in inputs:
			inputs.remove(s)
		if s in outputs:
			outputs.remove(s)
		if s in message_queues:
			del message_queues[s]
		s.close()

	def handle_client(r, host, file):
		sockaddr = None
		try:
			addrinfo = getaddrinfo(host=host, port=80, family=AF_INET, type=SOCK_STREAM)
			sockaddr = addrinfo[0][-1]
		except:
			pass

		if not sockaddr:
			clean_up_sock(r)
			return

		sock = socket(AF_INET, SOCK_STREAM)
		sock.setblocking(False)
		sock.settimeout(False)

		try:
			sock.connect(sockaddr)
		except:
			pass

		client_mappings[sock] = r
		message_queues[sock] = queue.Queue()

		request = (
				f'GET /{file} HTTP/1.1\r\n'
				f'Host: {host}\r\n'
				'\r\n'
				).encode()

		message_queues[sock].put(request)
		inputs.append(sock)
		if sock not in outputs:
			outputs.append(sock)

	def forward(r, data):
		try:
			message_queues[client_mappings[r]].put(data)
			if client_mappings[r] not in outputs:
				outputs.append(client_mappings[r])
		except KeyError:
			clean_up_sock(r)
		
	while inputs:
		readable, writable, exceptional = select.select(inputs, outputs, inputs)

		for r in readable:
			if r is server:
				conn, addr = server.accept()
				conn.setblocking(False)
				inputs.append(conn)
				message_queues[conn] = queue.Queue()
				continue

			# print(r.getpeername(), end=' ')

			try:
				data = r.recv(4096)
			except (BrokenPipeError, ConnectionResetError):
				clean_up_sock(r)
				continue

			if not data:
				clean_up_sock(r)
				continue

			try:
				msg = data.decode()
				headers = msg.split('\r\n')
			except:
				headers = []

			# print([h[:min(len(h), 50)] for h in headers[:2]])

			if len(headers) > 1 and headers[1] == 'Host: localhost:8888':
				url_components = headers[0].split(' ')[1].split('/')
				host = url_components[1]
				file = '' if len(url_components) < 3 else '/'.join(url_components[2:]) + '/'
				handle_client(r, host, file)
			else:
				forward(r, data)	

		for w in writable:
			try:
				# ip, port = w.getpeername()
				# if port == 443:
				# 	context.wrap_socket(w, server_hostname=ip)
				w.send(message_queues[w].get_nowait())
			except queue.Empty:
				outputs.remove(w)
			except:
				clean_up_sock(w)

		for e in exceptional:
			clean_up_sock(e)	

		# Extract the filename from the given message
		
		
		
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
