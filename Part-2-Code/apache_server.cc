// apache_server.cc
//
// A simple thread-per-connection TCP server (Apache prefork/worker style).
// The main thread listens for incoming connections; for each accepted
// connection it launches a new thread that serves that connection with
// blocking I/O until the client disconnects.
//
// Protocol: newline-delimited messages. For every line "<msg>\n" received,
// the server replies "Server received: <msg>\n".
//
// Build: g++ -std=c++17 -O2 -pthread apache_server.cc -o apache_server
// Run:   ./apache_server [port]        (default port 8080)
// Test:  echo "hello" | nc localhost 8080

#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <signal.h>
#include <sys/socket.h>
#include <unistd.h>

#include <atomic>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <string_view>
#include <system_error>
#include <thread>

namespace {

constexpr int kDefaultPort = 8080;
constexpr int kBacklog = 4096;  // Also capped by net.core.somaxconn.
constexpr size_t kBufferSize = 4096;
constexpr size_t kMaxLineSize = 64 * 1024;
constexpr std::string_view kReplyPrefix = "Server received: ";

std::atomic<int> g_active_connections{0};

// Writes the entire buffer, handling partial writes and EINTR.
bool SendAll(int fd, const char* data, size_t len) {
  while (len > 0) {
    ssize_t n = send(fd, data, len, MSG_NOSIGNAL);
    if (n < 0) {
      if (errno == EINTR) continue;
      return false;
    }
    data += n;
    len -= static_cast<size_t>(n);
  }
  return true;
}

// Extracts every complete line from `in`, appends one reply per line to
// `out`, and leaves any trailing partial line in `in`.
void ProcessLines(std::string& in, std::string& out) {
  size_t start = 0;
  size_t pos;
  while ((pos = in.find('\n', start)) != std::string::npos) {
    std::string_view msg(in.data() + start, pos - start);
    if (!msg.empty() && msg.back() == '\r') msg.remove_suffix(1);
    out.append(kReplyPrefix);
    out.append(msg);
    out.push_back('\n');
    start = pos + 1;
  }
  in.erase(0, start);
}

// Per-connection handler: serve messages until the client closes.
void HandleConnection(int client_fd) {
  std::string in;
  std::string out;
  char buf[kBufferSize];

  while (true) {
    ssize_t n = recv(client_fd, buf, sizeof(buf), 0);
    if (n < 0) {
      if (errno == EINTR) continue;
      break;
    }
    if (n == 0) break;  // Client closed the connection.

    in.append(buf, static_cast<size_t>(n));
    ProcessLines(in, out);
    if (in.size() > kMaxLineSize) break;  // Line too long; drop the client.

    if (!out.empty()) {
      if (!SendAll(client_fd, out.data(), out.size())) break;
      out.clear();
    }
  }

  close(client_fd);
  --g_active_connections;
}

}  // namespace

int main(int argc, char* argv[]) {
  int port = argc > 1 ? std::atoi(argv[1]) : kDefaultPort;
  if (port <= 0 || port > 65535) {
    std::cerr << "Invalid port: " << (argc > 1 ? argv[1] : "") << "\n";
    return 1;
  }

  signal(SIGPIPE, SIG_IGN);

  int listen_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (listen_fd < 0) {
    perror("socket");
    return 1;
  }

  int opt = 1;
  setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = htonl(INADDR_ANY);
  addr.sin_port = htons(static_cast<uint16_t>(port));

  if (bind(listen_fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
    perror("bind");
    close(listen_fd);
    return 1;
  }
  if (listen(listen_fd, kBacklog) < 0) {
    perror("listen");
    close(listen_fd);
    return 1;
  }

  std::cout << "apache_server (thread-per-connection) listening on port "
            << port << std::endl;

  while (true) {
    int client_fd = accept(listen_fd, nullptr, nullptr);
    if (client_fd < 0) {
      if (errno == EINTR) continue;
      perror("accept");
      if (errno == EMFILE || errno == ENFILE) usleep(10000);
      continue;
    }

    int one = 1;
    setsockopt(client_fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));

    // Launch a new thread for this connection; detach so it cleans up itself.
    try {
      ++g_active_connections;
      std::thread(HandleConnection, client_fd).detach();
    } catch (const std::system_error& e) {
      std::cerr << "Failed to create thread: " << e.what() << "\n";
      --g_active_connections;
      close(client_fd);
    }
  }

  close(listen_fd);
  return 0;
}
