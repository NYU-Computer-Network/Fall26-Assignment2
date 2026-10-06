# Thread-per-connection vs. epoll: echo server benchmark

This benchmark compares two TCP server designs under the same client load:

| File               | Design                                                                                     |
|--------------------|--------------------------------------------------------------------------------------------|
| `apache_server.cc` | **Thread per connection.** The main thread accepts connections and starts a new thread for each one. That thread uses blocking I/O until the client disconnects. |
| `nginx_server.cc`  | **Single-threaded epoll.** One thread handles the listening socket and every client connection, using non-blocking sockets. |
| `client.cc`        | **Benchmark client.** Starts N threads (N simulated clients). Each client sends M messages one at a time, waiting for each reply, and then the client prints the RTT distribution. |

## Protocol

Each message is one line, ending in `\n`. The servers echo every line back with a prefix:

```
request: "<send_ts_ns> <payload>\n"
reply:   "Server received: <send_ts_ns> <payload>\n"
```

The client puts its send timestamp (monotonic clock, in nanoseconds) in each request. The server echoes the line back without parsing it. When the reply arrives, the client computes:

```
RTT = (time the reply was read) - <send_ts_ns> echoed in the reply
```

Both timestamps come from the client's clock, so RTT is valid even when the client and server run on different machines.

## Requirements

- Linux (`nginx_server` uses epoll)
- A C++17 compiler, such as `sudo apt install g++`

## Build

```bash
g++ -std=c++17 -O2 -pthread apache_server.cc -o apache_server
g++ -std=c++17 -O2          nginx_server.cc  -o nginx_server
g++ -std=c++17 -O2 -pthread client.cc        -o client
```

## Run

Start **one** server at a time. Both listen on port 8080 by default.

```bash
./apache_server [port]
./nginx_server  [port]
```

Run the client in another terminal:

```bash
./client <host> <port> <N clients> <M messages per client> [msg_size=64]

# example: 100 clients x 10000 messages, 64-byte payload
./client 127.0.0.1 8080 100 10000
```

Quick check that a server is working:

```bash
echo "123 hello" | nc localhost 8080
# -> Server received: 123 hello
```

### Client output

```
Clients connected : 100 / 100
Messages OK       : 1000000
Errors            : 0
Elapsed           : ... s
Throughput        : ... msg/s
RTT (us)          : avg ...  p50 ...  p90 ...  p95 ...
```

- All N clients connect first, and then they all start sending at the same moment. `Elapsed` covers only the message exchange, not connection setup.
- RTTs from every thread are merged into one distribution after all threads finish.
- The client exits with a non-zero status if any client failed to connect or any reply was wrong or missing.

## Benchmark procedure

The servers run on `cn-fall26-server`, which has a single CPU, and the client runs on `cn-fall26-client`. With one CPU, both servers get the same amount of CPU time: `apache_server`'s threads all share that core, just like `nginx_server`'s single thread. Running the client on a separate machine also keeps it from competing with the server for CPU.

```bash
# on cn-fall26-server
ulimit -n 65536
./apache_server 8080

# on cn-fall26-client
ulimit -n 65536
for n in 1 10 20 50 100 200 500; do
  echo "== N=$n"
  ./client <server-ip> 8080 $n 10000
done
```

Stop the server with Ctrl+C, start `./nginx_server 8080`, and run the same loop again.

Things to record for each N:

- **Throughput** and **RTT p50/p90/p95/avg**, from the client output.
- **Server memory and CPU.** For example, run the server under `/usr/bin/time -v` (look at "Maximum resident set size"), or watch `top -p <pid>`. With thousands of connections, the thread-per-connection server needs a thread and a stack for each one. That cost is where it falls behind most clearly.

### System settings for large N

```bash
ulimit -n 65536                           # one file descriptor per connection (both shells)
sudo sysctl -w net.core.somaxconn=4096    # pending-connection queue (servers request 4096)
```


## Implementation notes

- Both servers handle messages the same way (`ProcessLines`): they buffer partial reads, reply to every complete line, and disconnect a client whose line grows past 64 KB without a `\n`.
- `TCP_NODELAY` is set on every connection, so small replies are sent immediately.
- `nginx_server` uses level-triggered epoll. It asks to be woken for writing (`EPOLLOUT`) only while a reply couldn't be sent in full, for example a large payload that fills the socket send buffer. Without that, a partially sent reply would leave the connection stuck.
- Neither server logs per message, so logging doesn't skew the results.
