Usage
Create an NS record that will point to where ever server.py is running

Update send.example.com in client/server to your own DNS name server.

Run server.py, and connect to it with netcat to send and receive traffic.
Run client.py on another machine and it will call out to server.py

That's it.