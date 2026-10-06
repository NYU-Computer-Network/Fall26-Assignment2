#!/usr/bin/env python3

import socket
import sys

def main():
    host = '35.247.25.42'
    port = 8080

    # Parse command line arguments
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    try:
        # Create a TCP socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print(f"Connecting to {host}:{port}...")
        client_socket.connect((host, port))
        print("Connected!")

        # Initial handshake: Receive authentication prompt from server
        prompt = client_socket.recv(1024).decode('utf-8')
        if not prompt:
            print("Server closed connection")
            return
        print(f"Server: {prompt.strip()}")

        # Initial handshake: Send student ID for authentication
        student_id = input("Enter your student ID: ")
        client_socket.send(student_id.encode('utf-8'))
        print(f"Sent: {student_id}")

        # Round 1: Receive server's rock-paper-scissors choice (P/R/S)
        server_choice = client_socket.recv(1).decode('utf-8')
        if not server_choice:
            print("Server closed connection")
            return
        print(f"Server's choice: {server_choice.strip()}")

        # Round 1: Send your rock-paper-scissors choice (P/R/S)
        your_choice = input("Enter your choice (P=Paper, R=Rock, S=Scissors): ")
        client_socket.send(your_choice.encode('utf-8'))
        print(f"Sent: {your_choice}")

        # Round 2: Receive game result (win/lose and token if you won)
        result = client_socket.recv(1024).decode('utf-8')
        if not result:
            print("Server closed connection")
            return
        print(f"Result: {result.strip()}")

    except socket.timeout:
        print("Connection timed out")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the server running on {host}:{port}?")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()
        print("Connection closed")

if __name__ == "__main__":
    main()
