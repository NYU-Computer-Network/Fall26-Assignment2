// client.cc
//
// Benchmark client for apache_server / nginx_server.
//
// Launches N threads; each thread opens one TCP connection (one simulated
// client) and performs M request/reply round trips: send a message, wait for
// the full reply, then send the next. All threads connect first and then
// start sending at the same moment, so the measured time covers only the
// message exchange.
//
// Protocol (newline-delimited):
//   request: "<send_ts_ns> <payload>\n"
//   reply:   "Server received: <send_ts_ns> <payload>\n"
//
// RTT = (time the client read the reply) - <send_ts_ns> echoed in the reply.
// Both timestamps come from the client's own clock.
//
// After every thread has sent its M requests, the RTTs from all threads are
// merged and the distribution is printed.
//
// Build: g++ -std=c++17 -O2 -pthread client.cc -o client
// Run:   ./client <host> <port> <num_clients N> <msgs_per_client M> [msg_size]
//   e.g. ./client 127.0.0.1 8080 100 10000 64

#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

namespace {

constexpr std::string_view kReplyPrefix = "Server received: ";

struct ClientResult {
  bool connected = false;
  uint64_t completed = 0;          // Successful round trips.
  uint64_t errors = 0;             // Failed or malformed replies.
  std::vector<uint64_t> rtts_ns;   // Round-trip time per message.
};

// Start gate: every thread connects, reports ready, then waits for "go".
struct StartGate {
  std::mutex mu;
  std::condition_variable cv;
  int ready = 0;
  bool go = false;

  void ArriveAndWait() {
    std::unique_lock<std::mutex> lock(mu);
    ++ready;
    cv.notify_all();
    cv.wait(lock, [this] { return go; });
  }
  void WaitForAll(int n) {
    std::unique_lock<std::mutex> lock(mu);
    cv.wait(lock, [&] { return ready >= n; });
  }
  void Open() {
    std::lock_guard<std::mutex> lock(mu);
    go = true;
    cv.notify_all();
  }
};

// Monotonic time in nanoseconds; used for both send and receive timestamps.
uint64_t NowNs() {
  return static_cast<uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(
          std::chrono::steady_clock::now().time_since_epoch())
          .count());
}

// Parses a leading unsigned decimal number followed by a space from `s`,
// advancing `s` past the space. Returns false if the format does not match.
bool ConsumeTimestamp(std::string_view& s, uint64_t& value) {
  size_t i = 0;
  value = 0;
  while (i < s.size() && s[i] >= '0' && s[i] <= '9') {
    value = value * 10 + static_cast<uint64_t>(s[i] - '0');
    ++i;
  }
  if (i == 0 || i >= s.size() || s[i] != ' ') return false;
  s.remove_prefix(i + 1);
  return true;
}

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

// Reads from fd until a full line is available in `buf`; moves that line
// (without '\n') into `line`. Returns false on error or EOF.
bool ReadLine(int fd, std::string& buf, std::string& line) {
  char tmp[4096];
  size_t pos;
  while ((pos = buf.find('\n')) == std::string::npos) {
    ssize_t n = recv(fd, tmp, sizeof(tmp), 0);
    if (n < 0) {
      if (errno == EINTR) continue;
      return false;
    }
    if (n == 0) return false;
    buf.append(tmp, static_cast<size_t>(n));
  }
  line.assign(buf, 0, pos);
  buf.erase(0, pos + 1);
  return true;
}

int Connect(const addrinfo* addrs) {
  for (const addrinfo* ai = addrs; ai != nullptr; ai = ai->ai_next) {
    int fd = socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);
    if (fd < 0) continue;
    if (connect(fd, ai->ai_addr, ai->ai_addrlen) == 0) {
      int one = 1;
      setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
      return fd;
    }
    close(fd);
  }
  return -1;
}

void RunClient(const addrinfo* addrs, int msgs, size_t msg_size,
               StartGate& gate, ClientResult& result) {
  int fd = Connect(addrs);
  result.connected = fd >= 0;
  gate.ArriveAndWait();
  if (fd < 0) return;

  const std::string payload(msg_size, 'x');
  result.rtts_ns.reserve(static_cast<size_t>(msgs));

  std::string request;
  std::string buf;
  std::string reply;
  for (int i = 0; i < msgs; ++i) {
    const uint64_t send_ns = NowNs();
    request = std::to_string(send_ns);
    request.push_back(' ');
    request.append(payload);
    request.push_back('\n');

    if (!SendAll(fd, request.data(), request.size()) ||
        !ReadLine(fd, buf, reply)) {
      result.errors += static_cast<uint64_t>(msgs - i);  // Connection lost.
      break;
    }
    const uint64_t client_recv_ns = NowNs();

    // Parse "Server received: <echoed_send_ns> <payload>".
    std::string_view rest(reply);
    uint64_t echoed_send_ns;
    if (rest.substr(0, kReplyPrefix.size()) != kReplyPrefix) {
      ++result.errors;
      continue;
    }
    rest.remove_prefix(kReplyPrefix.size());
    if (!ConsumeTimestamp(rest, echoed_send_ns) || rest != payload ||
        echoed_send_ns != send_ns) {
      ++result.errors;
      continue;
    }

    ++result.completed;
    result.rtts_ns.push_back(client_recv_ns - echoed_send_ns);
  }
  close(fd);
}

double PercentileUs(const std::vector<uint64_t>& sorted, double p) {
  if (sorted.empty()) return 0;
  size_t idx = static_cast<size_t>(p / 100.0 * (sorted.size() - 1));
  return static_cast<double>(sorted[idx]) / 1000.0;
}

}  // namespace

int main(int argc, char* argv[]) {
  if (argc < 5) {
    std::cerr << "Usage: " << argv[0]
              << " <host> <port> <num_clients N> <msgs_per_client M>"
                 " [msg_size=64]\n";
    return 1;
  }
  const char* host = argv[1];
  const char* port = argv[2];
  int num_clients = std::atoi(argv[3]);
  int msgs = std::atoi(argv[4]);
  size_t msg_size = argc > 5 ? static_cast<size_t>(std::atol(argv[5])) : 64;
  if (num_clients <= 0 || msgs <= 0) {
    std::cerr << "N and M must be positive\n";
    return 1;
  }

  addrinfo hints{};
  hints.ai_family = AF_UNSPEC;
  hints.ai_socktype = SOCK_STREAM;
  addrinfo* addrs = nullptr;
  if (int rc = getaddrinfo(host, port, &hints, &addrs); rc != 0) {
    std::cerr << "getaddrinfo: " << gai_strerror(rc) << "\n";
    return 1;
  }

  std::vector<ClientResult> results(static_cast<size_t>(num_clients));
  std::vector<std::thread> threads;
  threads.reserve(static_cast<size_t>(num_clients));
  StartGate gate;

  for (int i = 0; i < num_clients; ++i) {
    threads.emplace_back(RunClient, addrs, msgs, msg_size, std::ref(gate),
                         std::ref(results[static_cast<size_t>(i)]));
  }

  gate.WaitForAll(num_clients);
  auto start = std::chrono::steady_clock::now();
  gate.Open();
  for (auto& t : threads) t.join();
  double elapsed_s = std::chrono::duration<double>(
                         std::chrono::steady_clock::now() - start)
                         .count();
  freeaddrinfo(addrs);

  // All threads are done: merge their RTTs into one distribution.
  int connected = 0;
  uint64_t completed = 0;
  uint64_t errors = 0;
  size_t total_samples = 0;
  for (const auto& r : results) {
    connected += r.connected ? 1 : 0;
    completed += r.completed;
    errors += r.errors;
    total_samples += r.rtts_ns.size();
  }

  std::vector<uint64_t> rtts;
  rtts.reserve(total_samples);
  for (auto& r : results) {
    rtts.insert(rtts.end(), r.rtts_ns.begin(), r.rtts_ns.end());
    std::vector<uint64_t>().swap(r.rtts_ns);
  }
  std::sort(rtts.begin(), rtts.end());
  double rtt_sum_ns = 0;
  for (uint64_t v : rtts) rtt_sum_ns += static_cast<double>(v);
  const double n = rtts.empty() ? 1.0 : static_cast<double>(rtts.size());

  std::cout << std::fixed << std::setprecision(2);
  std::cout << "Clients connected : " << connected << " / " << num_clients
            << "\n";
  std::cout << "Messages OK       : " << completed << "\n";
  std::cout << "Errors            : " << errors << "\n";
  std::cout << "Elapsed           : " << elapsed_s << " s\n";
  std::cout << "Throughput        : " << completed / elapsed_s << " msg/s\n";
  std::cout << "RTT (us)          : avg " << rtt_sum_ns / n / 1000.0
            << "  p50 " << PercentileUs(rtts, 50)
            << "  p90 " << PercentileUs(rtts, 90)
            << "  p95 " << PercentileUs(rtts, 95) << "\n";

  return errors == 0 && connected == num_clients ? 0 : 1;
}
