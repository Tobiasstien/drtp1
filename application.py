import argparse
import socket
import struct
import time
import sys
from datetime import datetime

# Define constants
HEADER_SIZE = 8  # Size of packet header in bytes
MAX_DATA_SIZE = 992  # Maximum data payload size
TIMEOUT = 0.4  # Socket timeout in seconds
DEFAULT_PORT = 8080  # Default port for server

# Define flag bits for packet control
SYN = 0b0010  # Connection initiation flag
ACK = 0b0001  # Acknowledgment flag
FIN = 0b0100  # Connection termination flag
RESET = 0b1000  # Connection reset flag

def log(message):
    # Print a timestamped message for debugging
    print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- {message}")

def create_packet(seq=0, ack=0, flags=0, window=0, data=b''):
    # Create a packet by packing header fields and adding data
    header = struct.pack('!HHHH', seq, ack, flags, window)  # Pack header in network byte order
    return header + data  # Combine header with data payload

def parse_packet(packet):
    # Extract components from a packet into separate fields
    seq, ack, flags, window = struct.unpack('!HHHH', packet[:HEADER_SIZE])  # Unpack header
    data = packet[HEADER_SIZE:] if len(packet) > HEADER_SIZE else b''  # Extract data if present
    return seq, ack, flags, window, data

def run_server(ip, port, discard_seq=None):
    # Start server to receive data using reliable protocol
    server_start_time = time.time()
    
    # Create and setup UDP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((ip, port))  # Bind to specified IP and port
    server.settimeout(TIMEOUT)  # Set socket timeout
    log(f"Server listening on {ip}:{port}")
    
    # Wait for SYN from client (step 1 of 3-way handshake)
    connection_start_time = time.time()
    while True:
        try:
            data, client_addr = server.recvfrom(HEADER_SIZE + MAX_DATA_SIZE)
            _, _, flags, _, _ = parse_packet(data)
            
            if flags & SYN:
                print("SYN packet is received")
                
                # Send SYN-ACK (step 2 of 3-way handshake)
                syn_ack = create_packet(flags=SYN|ACK, window=15)  # Set window size to 15
                server.sendto(syn_ack, client_addr)
                print("SYN-ACK packet is sent")
                break
        except socket.timeout:
            continue  # Keep waiting if timeout occurs
    
    # Wait for ACK (final step of 3-way handshake)
    while True:
        try:
            data, _ = server.recvfrom(HEADER_SIZE + MAX_DATA_SIZE)
            _, _, flags, _, _ = parse_packet(data)
            
            if flags & ACK:
                print("ACK packet is received")
                print("Connection established")
                connection_time = time.time() - connection_start_time
                print(f"Connection establishment took {connection_time:.2f} seconds")
                break
        except socket.timeout:
            server.sendto(syn_ack, client_addr)  # Resend SYN-ACK if timeout
            continue
    
    # Data transfer phase
    data_transfer_start_time = time.time()
    expected_seq = 1  # Start expecting sequence number 1
    received_data = bytearray()  # Buffer for received data
    start_time = time.time()  # For throughput calculation
    bytes_received = 0
    has_discarded = False  # For simulating packet loss
    
    while True:
        try:
            packet, _ = server.recvfrom(HEADER_SIZE + MAX_DATA_SIZE)
            seq, _, flags, _, data = parse_packet(packet)
            
            # Check if FIN packet received (connection termination)
            if flags & FIN:
                print("FIN packet is received")
                fin_ack = create_packet(flags=FIN|ACK)  # Send FIN-ACK
                server.sendto(fin_ack, client_addr)
                print("FIN ACK packet is sent")
                
                # Calculate throughput statistics
                elapsed = time.time() - start_time
                throughput = (bytes_received * 8) / (elapsed * 1000000)  # Convert to Mbps
                print(f"\nThe throughput is {throughput:.2f} Mbps")
                data_transfer_time = time.time() - data_transfer_start_time
                print(f"Data Transfer finished in {data_transfer_time:.2f} seconds")
                print("Connection Closes")
                
                # Save received data to file
                with open("received_file", "wb") as f:
                    f.write(received_data)
                break
            
            # Process data packets
            if len(data) > 0:
                # Simulate packet loss for testing if requested
                if discard_seq and seq == discard_seq and not has_discarded:
                    has_discarded = True
                    log(f"out-of-order packet {seq} is received")
                    continue
                
                # Check if packet is the one we expect
                if seq == expected_seq:
                    log(f"packet {seq} is received")
                    received_data.extend(data)  # Add data to buffer
                    bytes_received += len(data)
                    
                    # Send ACK for received packet
                    ack_packet = create_packet(seq=seq, flags=ACK, window=15)
                    server.sendto(ack_packet, client_addr)
                    log(f"sending ack for the received {seq}")
                    expected_seq += 1  # Increment expected sequence number
                else:
                    log(f"out-of-order packet {seq} is received")  # Packet received out of order
        except socket.timeout:
            continue  # Keep waiting if timeout occurs
    
    server.close()  # Close socket when done

def run_client(filename, server_ip, server_port, window_size):
    # Start client to send data using reliable protocol
    client_start_time = time.time()
    
    # Create UDP socket
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(TIMEOUT)  # Set socket timeout
    
    # Set server address
    server_addr = (server_ip, server_port)
    
    # Connection establishment (3-way handshake)
    print("\nConnection Establishment Phase:\n")
    connection_start_time = time.time()
    
    # Send SYN 
    syn = create_packet(flags=SYN, window=window_size)
    client.sendto(syn, server_addr)
    print("SYN packet is sent")
    
    # Wait for SYN-ACK 
    syn_ack_received = False
    start_time = time.time()
    
    while time.time() - start_time < 5:  # 5-second timeout for connection
        try:
            data, addr = client.recvfrom(HEADER_SIZE + MAX_DATA_SIZE)
            server_addr = addr  # Update server address with actual responding address
            _, _, flags, server_window, _ = parse_packet(data)
            
            # Check if SYN-ACK received
            if (flags & SYN) and (flags & ACK):
                print("SYN-ACK packet is received")
                
                # Negotiate window size (use minimum of client and server window)
                window_size = min(window_size, server_window)
                
                # Send ACK 
                ack = create_packet(flags=ACK)
                client.sendto(ack, server_addr)
                print("ACK packet is sent")
                print("Connection established")
                connection_time = time.time() - connection_start_time
                print(f"Connection establishment took {connection_time:.2f} seconds")
                
                syn_ack_received = True
                break
                
        except socket.timeout:
            log("Timeout waiting for SYN-ACK, retrying")
            client.sendto(syn, server_addr)  # Resend SYN if timeout
    
    # Check if connection established successfully
    if not syn_ack_received:
        print("\nConnection failed - timeout\n")
        client.close()
        return
        
    # Read the file to be transferred
    file_read_start = time.time()
    try:
        with open(filename, 'rb') as f:
            file_data = f.read()  # Read entire file into memory
        file_read_time = time.time() - file_read_start
        log(f"Successfully read {len(file_data)} bytes from file in {file_read_time:.2f} seconds")
    except Exception as e:
        print(f"Error reading file: {e}")
        client.close()
        return
    
    # Split file into chunks of MAX_DATA_SIZE
    chunks = []
    for i in range(0, len(file_data), MAX_DATA_SIZE):
        chunks.append(file_data[i:i + MAX_DATA_SIZE])
    
    # Data transfer with Go-Back-N protocol
    print("\nData Transfer:\n")
    data_transfer_start_time = time.time()
    base = 1  # First unacknowledged packet
    next_seq = 1  # Next sequence to send
    window = {}  # Track packets in current window
    
    # Continue until all packets are acknowledged
    while base <= len(chunks):
        # Send packets in window
        while next_seq < base + window_size and next_seq <= len(chunks):
            packet = create_packet(seq=next_seq, data=chunks[next_seq-1])  # Create packet with data chunk
            client.sendto(packet, server_addr)  # Send the packet
            window[next_seq] = packet  # Store in window for possible retransmission
            
            # Log current window state
            window_str = "{" + ", ".join(str(s) for s in sorted(window.keys())) + "}"
            log(f"packet with seq = {next_seq} is sent, sliding window = {window_str}")
            next_seq += 1
        
        # Wait for ACK or timeout
        try:
            data, _ = client.recvfrom(HEADER_SIZE + MAX_DATA_SIZE)
            seq, _, flags, _, _ = parse_packet(data)
            
            if flags & ACK:
                log(f"ACK for packet = {seq} is received")
                
                # Remove acknowledged packets from window
                for s in list(window.keys()):
                    if s <= seq:
                        del window[s]  # Remove acknowledged packets
                
                # Advance base (first unacknowledged packet)
                base = seq + 1
                
        except socket.timeout:
            # Timeout - retransmit all packets in window (Go-Back-N)
            log("RTO occured")
            for seq in sorted(window.keys()):
                log(f"retransmitting packet with seq =  {seq}")
                client.sendto(window[seq], server_addr)  # Resend unacknowledged packets
    
    # Calculate and display data transfer time
    data_transfer_time = time.time() - data_transfer_start_time
    print(f"\nData Transfer finished in {data_transfer_time:.2f} seconds")
    
    # Connection teardown
    print("\nConnection Teardown:\n")
    teardown_start_time = time.time()
    
    # Send FIN to close connection
    fin = create_packet(flags=FIN)
    client.sendto(fin, server_addr)
    print("FIN packet is sent")
    
    # Wait for FIN-ACK
    try:
        while True:
            data, _ = client.recvfrom(HEADER_SIZE + MAX_DATA_SIZE)
            _, _, flags, _, _ = parse_packet(data)
            
            if (flags & FIN) and (flags & ACK):
                print("FIN ACK packet is received")
                teardown_time = time.time() - teardown_start_time
                print("Connection Closes")
                break
    except socket.timeout:
        log("Timeout waiting for FIN-ACK, retrying")
        client.sendto(fin, server_addr)  # Resend FIN if timeout
    
    client.close()  # Close socket when done

def main():
    # Parse command-line arguments and run the application
    parser = argparse.ArgumentParser(description='DATA2410 Reliable Transport Protocol')
    
    # Define mutually exclusive server/client mode options
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('-s', '--server', action='store_true', help='Run in server mode')
    mode.add_argument('-c', '--client', action='store_true', help='Run in client mode')
    
    # Define common options
    parser.add_argument('-i', '--ip', type=str, default='127.0.0.1', help='IP address')
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT, help='Port number')
    parser.add_argument('-f', '--file', type=str, help='File to transfer (client mode)')
    parser.add_argument('-w', '--window', type=int, default=3, help='Sliding window size')
    parser.add_argument('-d', '--discard', type=int, help='Sequence number to discard (testing)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.port < 1024 or args.port > 65535:
        print("Error: Port must be in range [1024, 65535]")
        sys.exit(1)
    
    if args.client and not args.file:
        print("Error: Client mode requires file (-f)")
        sys.exit(1)
    
    # Run server or client based on arguments
    try:
        if args.server:
            run_server(args.ip, args.port, args.discard)
        else:
            run_client(args.file, args.ip, args.port, args.window)
    except KeyboardInterrupt:
        print("\nApplication terminated by user")

if __name__ == "__main__":
    main()
