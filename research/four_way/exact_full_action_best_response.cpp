// Exact-rational full-action Game 2 response oracle.
// Input: support size, then allocations (five counts) and integer frequencies.
// Output: maximizing legal action and its exact expected-payout fraction.
// Frequencies must sum to <=1e12 so weighted numerators fit unsigned __int128.
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

using Allocation = std::array<int, 5>;
static constexpr std::array<int, 5> value{1, 2, 3, 4, 5};
static constexpr std::array<int, 4> prize4{36, 16, 8, 0};
using U128 = unsigned __int128;
using ScenarioScores = std::array<std::array<std::array<std::uint8_t, 4>, 101>, 5>;

struct OpponentTriple {
    U128 weighted_multiplicity;
    ScenarioScores score_increment{}; // castle, own count, player (self first)
};

static int payout_quarters(const std::array<int, 4>& score12) {
    int above = 0;
    int tied = 1;
    for (int player = 1; player < 4; ++player) {
        above += score12[player] > score12[0];
        tied += score12[player] == score12[0];
    }
    int prize_sum = 0;
    for (int rank = above; rank < above + tied; ++rank)
        prize_sum += prize4[rank];
    return prize_sum / tied;
}

static void precompute_scenario(OpponentTriple& scenario,
                                const Allocation& a, const Allocation& b,
                                const Allocation& c) {
    const std::array<const Allocation*, 3> opponents{&a, &b, &c};
    for (int castle = 0; castle < 5; ++castle) {
        int high = 0;
        for (auto opponent : opponents)
            high = std::max(high, (*opponent)[castle]);
        int opponent_leaders = 0;
        for (auto opponent : opponents)
            opponent_leaders += ((*opponent)[castle] == high);
        for (int own = 0; own <= 100; ++own) {
            auto& inc = scenario.score_increment[castle][own];
            if (own > high) {
                inc[0] = static_cast<std::uint8_t>(12 * value[castle]);
            } else if (own == high) {
                const int share = 12 * value[castle] / (opponent_leaders + 1);
                inc[0] = static_cast<std::uint8_t>(share);
                for (int player = 0; player < 3; ++player)
                    if ((*opponents[player])[castle] == high)
                        inc[player + 1] = static_cast<std::uint8_t>(share);
            } else {
                const int share = 12 * value[castle] / opponent_leaders;
                for (int player = 0; player < 3; ++player)
                    if ((*opponents[player])[castle] == high)
                        inc[player + 1] = static_cast<std::uint8_t>(share);
            }
        }
    }
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
        for (int& x : actions[i]) {
            std::cin >> x;
            if (x < 0 || x > 100) {
                std::cerr << "soldier counts must be in 0..100\n";
                return 2;
            }
            sum += x;
        }
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
                if (!weighted) continue;
                OpponentTriple scenario{};
                scenario.weighted_multiplicity = weighted;
                precompute_scenario(scenario, actions[i], actions[j], actions[k]);
                triples.push_back(std::move(scenario));
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
                    for (const auto& scenario : triples) {
                        std::array<int, 4> score12{};
                        for (int castle = 0; castle < 5; ++castle) {
                            const auto& inc = scenario.score_increment[castle]
                                                                       [candidate[castle]];
                            for (int player = 0; player < 4; ++player)
                                score12[player] += inc[player];
                        }
                        numerator += scenario.weighted_multiplicity
                                   * payout_quarters(score12);
                    }
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
