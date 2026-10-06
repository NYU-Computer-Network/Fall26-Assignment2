// nginx_server.cc
//
// A single-threaded, event-driven TCP server (nginx-worker style) built on
// epoll. One thread multiplexes the listening socket and every client
// connection using non-blocking I/O.
//
// Protocol (same as apache_server.cc): newline-delimited messages. For every
// line "<msg>\n" received, the server replies "Server received: <msg>\n".
//
// Build: g++ -std=c++17 -O2 nginx_server.cc -o nginx_server
// Run:   ./nginx_server [port]         (default port 8080)
// Test:  echo "hello" | nc localhost 8080

#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <signal.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <string_view>

namespace {

constexpr int kDefaultPort = 8080;
constexpr int kBacklog = 4096;  // Also capped by net.core.somaxconn.
constexpr int kMaxEvents = 1024;
constexpr size_t kBufferSize = 4096;
constexpr size_t kMaxLineSize = 64 * 1024;
constexpr std::string_view kReplyPrefix = "Server received: ";

struct Connection {
  int fd;
  std::string in;        // Bytes received but not yet forming a full line.
  std::string out;       // Reply bytes waiting to be sent.
  size_t out_offset = 0; // How much of `out` has already been sent.
  bool want_write = false;
};

int g_epoll_fd = -1;

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

void CloseConnection(Connection* conn) {
  epoll_ctl(g_epoll_fd, EPOLL_CTL_DEL, conn->fd, nullptr);
  close(conn->fd);
  delete conn;
}

// Subscribe to EPOLLOUT only while there is pending output, so we are not
// woken up constantly for a writable socket.
void SetWriteInterest(Connection* conn, bool want_write) {
  if (conn->want_write == want_write) return;
  epoll_event ev{};
  ev.events = EPOLLIN | (want_write ? EPOLLOUT : 0);
  ev.data.ptr = conn;
  epoll_ctl(g_epoll_fd, EPOLL_CTL_MOD, conn->fd, &ev);
  conn->want_write = want_write;
}

// Sends as much pending output as the socket accepts without blocking.
// Returns false if the connection should be closed.
bool FlushOutput(Connection* conn) {
  while (conn->out_offset < conn->out.size()) {
    ssize_t n = send(conn->fd, conn->out.data() + conn->out_offset,
                     conn->out.size() - conn->out_offset, MSG_NOSIGNAL);
    if (n < 0) {
      if (errno == EINTR) continue;
      if (errno == EAGAIN || errno == EWOULDBLOCK) break;
      return false;
    }
    conn->out_offset += static_cast<size_t>(n);
  }

  if (conn->out_offset == conn->out.size()) {
    conn->out.clear();
    conn->out_offset = 0;
    SetWriteInterest(conn, false);
  } else {
    SetWriteInterest(conn, true);  // Resume when the socket is writable.
  }
  return true;
}

// Reads available input, generates replies, and tries to send them.
// Returns false if the connection should be closed.
bool HandleReadable(Connection* conn) {
  char buf[kBufferSize];
  while (true) {
    ssize_t n = recv(conn->fd, buf, sizeof(buf), 0);
    if (n < 0) {
      if (errno == EINTR) continue;
      if (errno == EAGAIN || errno == EWOULDBLOCK) break;
      return false;
    }
    if (n == 0) return false;  // Client closed the connection.
    conn->in.append(buf, static_cast<size_t>(n));
    // Level-triggered: a short read means the socket is (likely) drained;
    // any leftover data will trigger another EPOLLIN.
    if (static_cast<size_t>(n) < sizeof(buf)) break;
  }

  ProcessLines(conn->in, conn->out);
  if (conn->in.size() > kMaxLineSize) return false;  // Line too long.
  return FlushOutput(conn);
}

void AcceptConnections(int listen_fd) {
  while (true) {
    int fd = accept4(listen_fd, nullptr, nullptr, SOCK_NONBLOCK);
    if (fd < 0) {
      if (errno == EINTR) continue;
      if (errno != EAGAIN && errno != EWOULDBLOCK) perror("accept4");
      return;
    }

    int one = 1;
    setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));

    auto* conn = new Connection{fd};
    epoll_event ev{};
    ev.events = EPOLLIN;
    ev.data.ptr = conn;
    if (epoll_ctl(g_epoll_fd, EPOLL_CTL_ADD, fd, &ev) < 0) {
      perror("epoll_ctl ADD");
      close(fd);
      delete conn;
    }
  }
}

}  // namespace

int main(int argc, char* argv[]) {
  int port = argc > 1 ? std::atoi(argv[1]) : kDefaultPort;
  if (port <= 0 || port > 65535) {
    std::cerr << "Invalid port: " << (argc > 1 ? argv[1] : "") << "\n";
    return 1;
  }

  signal(SIGPIPE, SIG_IGN);

  int listen_fd = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK, 0);
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
    return 1;
  }
  if (listen(listen_fd, kBacklog) < 0) {
    perror("listen");
    return 1;
  }

  g_epoll_fd = epoll_create(1);  // size is ignored since Linux 2.6.8 but must be > 0.
  if (g_epoll_fd < 0) {
    perror("epoll_create");
    return 1;
  }

  // The listening socket is tagged with a null pointer; connections carry
  // their Connection* in data.ptr.
  epoll_event listen_ev{};
  listen_ev.events = EPOLLIN;
  listen_ev.data.ptr = nullptr;
  if (/** TODO: you should replace this line and call some epool API here, 
          to add the handler listen_fd to the created epoll (represented by g_epoll_fd)  */ 1 < 0) {
    perror("epoll API ADD listen");
    return 1;
  }

  std::cout << "nginx_server (single-thread epoll) listening on port " << port
            << std::endl;

  epoll_event events[kMaxEvents];
  while (true) {
    // TODO: you should replace this line: int n = 0 
    int n = 0; // Here we should call some epoll API to monitor the poll of handlers(file descriptors, i.e., fds). 
    // The API will block here until some fds become active (i.e., readable/writable/has new connections, etc)
    if (n < 0) {
      if (errno == EINTR) continue;
      perror("epoll API returns error");
      break;
    }

    for (int i = 0; i < n; ++i) {
      if (events[i].data.ptr == nullptr) {
        // This is the listening socket, it is used to accept connections rather than receiving request data
        // TODO: Fill something here

        continue;
      }

      // If we did not trigger continue in line 219, then that means this is a handler representing connection
      // The follow-up logic is to handle the real connection: 
      // HandleReadable will do some operations if this connection is readable
      // FlushOutput will do some operations if this connection is writable
      auto* conn = static_cast<Connection*>(events[i].data.ptr);
      uint32_t ev = events[i].events;

      if (ev & (EPOLLERR | EPOLLHUP)) {
        CloseConnection(conn);
        continue;
      }
      if ((ev & EPOLLIN) && !HandleReadable(conn)) {
        CloseConnection(conn);
        continue;
      }
      if ((ev & EPOLLOUT) && !FlushOutput(conn)) {
        CloseConnection(conn);
        continue;
      }
    }
  }

  close(g_epoll_fd);
  close(listen_fd);
  return 0;
}
