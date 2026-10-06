#!/usr/bin/env python3

import socket
import sys

def main():
    host = '35.247.25.42' ## We will use this server IP
    port = 8081  # Hard server runs on port 8081

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

        # Play exactly 100 rounds (automatic mode)
        print("\n🤖 Playing...\n")

        TOTAL_ROUNDS = 100
        ## TODO: After you have sent your studentID and the authentication is passed 
        ## Then you will start playing the game for 100 rounds: 
        ## For every round, the server will send a letter: P|S|R
        ## You should reply a letter to win each round
        ## If you can successfully win 100 rounds, the server will send you a token
        ## Note: 1) Every round, you will only have 10 millisecond to reply, 
        ## otherwise, the server will shut down the connection. 
        ## That means, you cannot manually type the answer as previous game
        ## 2) If you lose any round in the middle, the server will shutdown the socket, too 

        # After 100 rounds, receive final victory message
        final_message = client_socket.recv(1024).decode('utf-8')
        if final_message:
            if "token" in final_message:
                print("🎉 WIN! " + final_message.strip())
            else:
                print("Unexpected final message ", final_message)

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
