Hvordan kjøre programmet

For å starte serveren, kjør:
python3 application.py -s -i <ip_address> -p <port>

Eksempel:
python3 application.py -s -i 0.0.0.0 -p 8080

Valgfrie parametere for serveren:
-d <seq_num>: Angi et sekvensnummer som skal forkastes (for testing av retransmisjon)

For å starte klienten og sende en fil til serveren, kjør:
python3 application.py -c -f <file_name> -i <server_ip> -p <server_port> -w <window_size>

Eksempel:
python3 application.py -c -f iceland-safiqul.jpg -i 127.0.0.1 -p 8080 -w 5

Parametere
-s, --server: Kjør som server (mottaker)
-c, --client: Kjør som klient (sender)
-i, --ip: IP-adresse (standard: 127.0.0.1)
-p, --port: Portnummer (standard: 8080)
-f, --file: Fil som skal overføres (påkrevd i klient-modus)
-w, --window: Størrelse på glidende vindu (standard: 3)
-d, --discard: Sekvensnummer som skal forkastes (kun server, for testing)

Kjøring i Mininet
For å teste programmet i Mininet, bruk den medfølgende simple-topo.py topologien:

sudo python3 simple-topo.py

I Mininet-konsollet, åpne to xterm-vinduer:
mininet> xterm h1 h2

I h2 (server):
python3 application.py -s -i 10.0.1.2 -p 8080

I h1 (klient):
python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8080 -w 5

Testkonfigurasjoner
For ytelsestesting, prøv ulike vindusstørrelser:

python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8080 -w 3
python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8080 -w 5
python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8080 -w 10
python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8080 -w 15
python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8080 -w 20
python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8080 -w 25

For testing av pakketap, bruk -d flagget på serveren:
python3 application.py -s -i 10.0.1.2 -p 8080 -d 1800

For testing av simulert pakketap:

Kommenter ut linje#43 net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 100ms")
og bruk linje#44: net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 100ms loss 2%").

På server:
python3 application.py -s -i 10.0.1.2 -p 8080

På klient:
python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8080 -w 5
# DRTP
