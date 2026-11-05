// Exact best response for the constant-sum homotopy auxiliary game.
// The action-dependent part of the interpolated payoff is
//   t * G_a(p) - (1-t) * c(a),
// where c(a0)=0, c(a1)=1, and otherwise
//   c(a)=2 + (a1 + 2*a2 + 3*a3 + 4*a4 + 5*a5)/5000.
// Frequencies are limited to 1e6 so all adjusted numerators fit signed __int128.
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

using Allocation = std::array<int, 5>;
static constexpr std::array<int, 5> value{1, 2, 3, 4, 5};
static constexpr std::array<int, 4> prize4{36, 16, 8, 0};
using U128 = unsigned __int128;
using I128 = __int128;
using ScenarioScores = std::array<std::array<std::array<std::uint8_t, 4>, 101>, 5>;

struct OpponentTriple {
    std::array<U128, 37> weighted_payout{};
    ScenarioScores score_increment{};
};
struct Candidate {
    Allocation action{};
    U128 numerator = 0;
    I128 adjusted = 0;
};
static bool better(const Candidate& a, const Candidate& b) {
    return a.adjusted != b.adjusted ? a.adjusted > b.adjusted
                                    : a.action < b.action;
}
static void insert_top(std::vector<Candidate>& top, const Candidate& candidate, int limit) {
    auto position = std::lower_bound(top.begin(), top.end(), candidate, better);
    if (position == top.end() && static_cast<int>(top.size()) >= limit) return;
    top.insert(position, candidate);
    if (static_cast<int>(top.size()) > limit) top.pop_back();
}
static int payout_quarters(const std::array<int, 4>& score12) {
    int above = 0, tied = 1;
    for (int player = 1; player < 4; ++player) {
        above += score12[player] > score12[0];
        tied += score12[player] == score12[0];
    }
    int sum = 0;
    for (int rank = above; rank < above + tied; ++rank) sum += prize4[rank];
    return sum / tied;
}
static void precompute_scenario(OpponentTriple& scenario, const Allocation& a,
                                const Allocation& b, const Allocation& c) {
    const std::array<const Allocation*, 3> opponents{&a, &b, &c};
    for (int castle = 0; castle < 5; ++castle) {
        int high = std::max({a[castle], b[castle], c[castle]});
        int leaders = (a[castle] == high) + (b[castle] == high) + (c[castle] == high);
        for (int own = 0; own <= 100; ++own) {
            auto& inc = scenario.score_increment[castle][own];
            if (own > high) inc[0] = static_cast<std::uint8_t>(12 * value[castle]);
            else if (own == high) {
                int share = 12 * value[castle] / (leaders + 1);
                inc[0] = static_cast<std::uint8_t>(share);
                for (int p = 0; p < 3; ++p)
                    if ((*opponents[p])[castle] == high) inc[p + 1] = static_cast<std::uint8_t>(share);
            } else {
                int share = 12 * value[castle] / leaders;
                for (int p = 0; p < 3; ++p)
                    if ((*opponents[p])[castle] == high) inc[p + 1] = static_cast<std::uint8_t>(share);
            }
        }
    }
}
static std::string to_string_u128(U128 n) {
    if (!n) return "0";
    std::string s;
    while (n) { s.push_back(char('0' + n % 10)); n /= 10; }
    std::reverse(s.begin(), s.end()); return s;
}
static std::string to_string_i128(I128 n) {
    if (n < 0) return "-" + to_string_u128(static_cast<U128>(-n));
    return to_string_u128(static_cast<U128>(n));
}
static std::uint64_t cost_numerator(const Allocation& a) {
    const Allocation a0{20,20,20,20,20}, a1{19,20,20,20,21};
    if (a == a0) return 0;
    if (a == a1) return 5000;
    int weighted = 0;
    for (int i = 0; i < 5; ++i) weighted += (i + 1) * a[i];
    return 10000 + weighted;
}
int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "usage: oracle THREADS TOP_K T_NUM T_DEN\n"; return 2;
    }
    int threads = std::stoi(argv[1]), top_k = std::stoi(argv[2]);
    std::uint64_t t_num = std::stoull(argv[3]), t_den = std::stoull(argv[4]);
    if (threads < 1 || threads > 256 || top_k < 1 || top_k > 1000 ||
        !t_den || t_num > t_den || t_den > 1000000) {
        std::cerr << "invalid oracle parameters\n"; return 2;
    }
    int n;
    if (!(std::cin >> n) || n <= 0) { std::cerr << "expected support size\n"; return 2; }
    std::vector<Allocation> actions(n);
    std::vector<std::uint64_t> weights(n);
    U128 total = 0;
    for (int i = 0; i < n; ++i) {
        int sum = 0;
        for (int& x : actions[i]) { std::cin >> x; sum += x; }
        std::cin >> weights[i];
        if (sum != 100 || weights[i] == 0) { std::cerr << "invalid support row\n"; return 2; }
        total += weights[i];
    }
    if (total == 0 || total > 1000000) { std::cerr << "frequency total must be <=1e6\n"; return 2; }
    std::vector<OpponentTriple> triples;
    for (int i = 0; i < n; ++i) for (int j = i; j < n; ++j) for (int k = j; k < n; ++k) {
        int mult = (i == j && j == k) ? 1 : (i == j || j == k) ? 3 : 6;
        U128 weighted = static_cast<U128>(mult) * weights[i] * weights[j] * weights[k];
        if (!weighted) continue;
        OpponentTriple s{};
        for (int q = 0; q <= 36; ++q) s.weighted_payout[q] = weighted * q;
        precompute_scenario(s, actions[i], actions[j], actions[k]);
        triples.push_back(std::move(s));
    }
    U128 denominator = 4 * total * total * total;
    int workers = std::min(threads, 101);
    std::vector<std::vector<Candidate>> results(workers);
    std::vector<std::thread> pool;
    for (int tid = 0; tid < workers; ++tid) pool.emplace_back([&,tid] {
        auto& local = results[tid];
        for (int a = tid; a <= 100; a += workers)
        for (int b = 0; b <= 100-a; ++b)
        for (int c = 0; c <= 100-a-b; ++c)
        for (int d = 0; d <= 100-a-b-c; ++d) {
            Allocation x{a,b,c,d,100-a-b-c-d}; U128 num = 0;
            for (const auto& s : triples) {
                std::array<int,4> scores{};
                for (int castle=0; castle<5; ++castle)
                    for (int p=0; p<4; ++p) scores[p] += s.score_increment[castle][x[castle]][p];
                num += s.weighted_payout[payout_quarters(scores)];
            }
            U128 lhs = static_cast<U128>(t_num) * num * 5000;
            U128 rhs = static_cast<U128>(t_den-t_num) * cost_numerator(x) * denominator;
            Candidate cand{x,num,static_cast<I128>(lhs)-static_cast<I128>(rhs)};
            if (static_cast<int>(local.size()) < top_k || better(cand,local.back())) insert_top(local,cand,top_k);
        }
    });
    for (auto& th:pool) th.join();
    std::vector<Candidate> global;
    for (const auto& local:results) for (const auto& x:local) insert_top(global,x,top_k);
    for (const auto& x:global)
        std::cout << x.action[0] << ',' << x.action[1] << ',' << x.action[2] << ',' << x.action[3] << ',' << x.action[4]
                  << '\t' << to_string_u128(x.numerator) << '\t' << to_string_u128(denominator)
                  << '\t' << to_string_i128(x.adjusted) << '\t' << triples.size() << '\n';
}
