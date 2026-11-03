// Exact-rational full-action best response oracle for a finite Game 2 mixture.
// Input: support size, then each allocation's five soldier counts and integer
// frequency. Output: lexicographically first maximizing action and its exact
// expected-payout fraction. Frequencies must sum to at most 1e12 so all weighted
// payout numerators fit unsigned __int128.
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

using Allocation = std::array<int, 5>;
static constexpr std::array<int, 5> value{1, 2, 3, 4, 5};
static constexpr std::array<int, 4> prize4{36, 16, 8, 0};
using U128 = unsigned __int128;

struct OpponentTriple {
    int a;
    int b;
    int c;
    U128 weighted_multiplicity;
};

static int payout_quarters(const Allocation& me, const Allocation& a,
                           const Allocation& b, const Allocation& c) {
    const std::array<const Allocation*, 4> players{&me, &a, &b, &c};
    std::array<int, 4> score12{};
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
            if (order[place] == 0) return shared_prize4;
        rank = end;
    }
    return 0;
}

static std::string to_string_u128(U128 n) {
    if (n == 0) return "0";
    std::string out;
    while (n) {
        out.push_back(static_cast<char>('0' + n % 10));
        n /= 10;
    }
    std::reverse(out.begin(), out.end());
    return out;
}

int main() {
    int n;
    if (!(std::cin >> n) || n <= 0) {
        std::cerr << "expected positive support size\n";
        return 2;
    }
    std::vector<Allocation> actions(n);
    std::vector<std::uint64_t> weights(n);
    U128 total = 0;
    for (int i = 0; i < n; ++i) {
        int sum = 0;
        for (int& x : actions[i]) { std::cin >> x; sum += x; }
        std::cin >> weights[i];
        if (sum != 100 || weights[i] == 0) {
            std::cerr << "invalid allocation or nonpositive frequency\n";
            return 2;
        }
        total += weights[i];
    }
    if (total == 0 || total > 1'000'000'000'000ULL) {
        std::cerr << "frequency total must be in 1..1e12\n";
        return 2;
    }

    std::vector<OpponentTriple> triples;
    for (int i = 0; i < n; ++i) {
        for (int j = i; j < n; ++j) {
            for (int k = j; k < n; ++k) {
                const int multiplicity = (i == j && j == k) ? 1
                                       : (i == j || j == k) ? 3 : 6;
                const U128 weighted = static_cast<U128>(multiplicity)
                                    * weights[i] * weights[j] * weights[k];
                if (weighted) triples.push_back({i, j, k, weighted});
            }
        }
    }

    Allocation best{};
    U128 best_numerator = 0;
    bool have_best = false;
    for (int a = 0; a <= 100; ++a)
        for (int b = 0; b <= 100 - a; ++b)
            for (int c = 0; c <= 100 - a - b; ++c)
                for (int d = 0; d <= 100 - a - b - c; ++d) {
                    const Allocation candidate{a, b, c, d, 100 - a - b - c - d};
                    U128 numerator = 0;
                    for (const auto& t : triples)
                        numerator += t.weighted_multiplicity
                                   * payout_quarters(candidate, actions[t.a],
                                                     actions[t.b], actions[t.c]);
                    if (!have_best || numerator > best_numerator) {
                        best = candidate;
                        best_numerator = numerator;
                        have_best = true;
                    }
                }

    const U128 denominator = 4 * total * total * total;
    std::cout << best[0];
    for (int i = 1; i < 5; ++i) std::cout << ',' << best[i];
    std::cout << '\t' << to_string_u128(best_numerator)
              << '\t' << to_string_u128(denominator)
              << '\t' << triples.size() << '\n';
}
