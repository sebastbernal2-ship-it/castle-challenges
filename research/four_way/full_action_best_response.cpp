// Exact full-action best response to a finite Game 2 population.
// Build: c++ -O3 -std=c++17 full_action_best_response.cpp -o /tmp/castle-br4
// Input: support size, then five soldier counts and a weight per support action.
// Output: best allocation and expected payout. Computation is exact in action
// enumeration and scoring; probability weights use long double arithmetic.
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <vector>

using Allocation = std::array<int, 5>;
static constexpr std::array<int, 5> value{1, 2, 3, 4, 5};
static constexpr std::array<int, 4> prize4{36, 16, 8, 0}; // payout * 4

struct OpponentTriple {
    const Allocation* a;
    const Allocation* b;
    const Allocation* c;
    long double probability;
};

static long double utility4(const Allocation& me, const Allocation& a,
                       const Allocation& b, const Allocation& c) {
    const std::array<const Allocation*, 4> players{&me, &a, &b, &c};
    std::array<int, 4> score12{}; // castle score * 12; exact integer units
    for (int castle = 0; castle < 5; ++castle) {
        int high = 0;
        for (auto p : players) high = std::max(high, (*p)[castle]);
        int leaders = 0;
        for (auto p : players) leaders += ((*p)[castle] == high);
        const int share = value[castle] * (12 / leaders);
        for (int i = 0; i < 4; ++i)
            if ((*players[i])[castle] == high) score12[i] += share;
    }
    std::array<int, 4> order{0, 1, 2, 3};
    std::sort(order.begin(), order.end(), [&](int x, int y) {
        return score12[x] > score12[y];
    });
    int rank = 0;
    while (rank < 4) {
        int end = rank + 1;
        while (end < 4 && score12[order[end]] == score12[order[rank]]) ++end;
        int prize_sum = 0;
        for (int place = rank; place < end; ++place) prize_sum += prize4[place];
        const int shared_prize4 = prize_sum / (end - rank);
        for (int place = rank; place < end; ++place)
            if (order[place] == 0) return shared_prize4 / 4.0L;
        rank = end;
    }
    return 0.0;
}

int main() {
    int n;
    if (!(std::cin >> n) || n <= 0) {
        std::cerr << "expected a positive support size\n";
        return 2;
    }
    std::vector<Allocation> actions(n);
    std::vector<long double> weights(n);
    long double total = 0.0L;
    for (int i = 0; i < n; ++i) {
        for (int& x : actions[i]) std::cin >> x;
        std::cin >> weights[i];
        int sum = 0;
        for (int x : actions[i]) {
            if (x < 0) { std::cerr << "negative soldiers\n"; return 2; }
            sum += x;
        }
        if (sum != 100 || !std::isfinite(weights[i]) || weights[i] < 0) {
            std::cerr << "invalid allocation or weight\n";
            return 2;
        }
        total += weights[i];
    }
    if (total <= 0) { std::cerr << "zero total weight\n"; return 2; }
    for (long double& w : weights) w /= total;

    std::vector<OpponentTriple> triples;
    for (int i = 0; i < n; ++i) {
        for (int j = i; j < n; ++j) {
            for (int k = j; k < n; ++k) {
                int multiplicity = 6;
                if (i == j && j == k) multiplicity = 1;
                else if (i == j || j == k) multiplicity = 3;
                const long double p = multiplicity * weights[i] * weights[j] * weights[k];
                if (p > 0)
                    triples.push_back({&actions[i], &actions[j], &actions[k], p});
            }
        }
    }

    Allocation best{};
    long double best_value = -1.0L;
    for (int a = 0; a <= 100; ++a)
        for (int b = 0; b <= 100 - a; ++b)
            for (int c = 0; c <= 100 - a - b; ++c)
                for (int d = 0; d <= 100 - a - b - c; ++d) {
                    const int e = 100 - a - b - c - d;
                    const Allocation candidate{a, b, c, d, e};
                    long double expected = 0.0L;
                    for (const auto& t : triples)
                        expected += t.probability * utility4(candidate, *t.a, *t.b, *t.c);
                    if (expected > best_value) {
                        best = candidate;
                        best_value = expected;
                    }
                }
    std::cout << std::setprecision(21) << best[0];
    for (int i = 1; i < 5; ++i) std::cout << ',' << best[i];
    std::cout << '\t' << best_value << '\t' << triples.size() << '\n';
}
