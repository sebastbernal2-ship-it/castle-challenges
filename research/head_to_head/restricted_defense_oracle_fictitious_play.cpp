// Fictitious play for a restricted attacker set and the full defense space.
// Attacker payoff is exact integer half-points. The defender's best response
// to an empirical attacker mixture is computed by the exact allocation DP.
// Input: number of attacker actions, rounds, then five soldiers per action.
// Output: upper bound, lower bound, support size, then defense actions/counts.
#include <algorithm>
#include <array>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <map>
#include <vector>

using Allocation = std::array<int, 5>;
static constexpr std::array<int, 5> values{1, 2, 3, 4, 5};

static int payoff2(const Allocation& a, const Allocation& b) {
    int result = 0;
    for (int i = 0; i < 5; ++i)
        result += a[i] > b[i] ? 2 * values[i]
                 : a[i] == b[i] ? values[i] : 0;
    return result;
}

static std::pair<Allocation, std::int64_t> best_defense(
        const std::int64_t hist[5][101]) {
    constexpr int S = 100;
    std::int64_t q[5][S + 1]{};
    std::int64_t dp[6][S + 1];
    int choice[6][S + 1]{};
    for (int c = 0; c < 5; ++c) {
        std::int64_t cumulative = 0;
        for (int x = 0; x <= S; ++x) {
            q[c][x] = (c + 1) * (2 * cumulative + hist[c][x]);
            cumulative += hist[c][x];
        }
    }
    constexpr std::int64_t NEG = INT64_MIN / 4;
    for (int c = 0; c <= 5; ++c)
        for (int used = 0; used <= S; ++used)
            dp[c][used] = NEG;
    dp[0][0] = 0;
    for (int c = 1; c <= 5; ++c)
        for (int used = 0; used <= S; ++used)
            for (int x = 0; x <= used; ++x) {
                const auto candidate = dp[c - 1][used - x] + q[c - 1][x];
                if (candidate > dp[c][used]) {
                    dp[c][used] = candidate;
                    choice[c][used] = x;
                }
            }
    Allocation action{};
    int remaining = S;
    for (int c = 5; c >= 1; --c) {
        action[c - 1] = choice[c][remaining];
        remaining -= action[c - 1];
    }
    return {action, dp[5][S]};
}

int main() {
    int m, rounds;
    if (!(std::cin >> m >> rounds) || m <= 0 || rounds <= 0) {
        std::cerr << "expected positive attacker count and rounds\n";
        return 2;
    }
    std::vector<Allocation> attackers(m);
    for (auto& a : attackers) {
        int total = 0;
        for (int& x : a) { std::cin >> x; total += x; }
        if (total != 100) { std::cerr << "invalid attacker allocation\n"; return 2; }
    }

    std::vector<std::int64_t> row_counts(m, 0), row_sums(m, 0);
    std::int64_t hist[5][101]{};
    row_counts[0] = 1; // deterministic seed for the attacker empirical mixture
    for (int c = 0; c < 5; ++c) ++hist[c][attackers[0][c]];
    auto [first_defense, ignored_score] = best_defense(hist);
    (void)ignored_score;
    std::map<Allocation, std::int64_t> defense_counts;
    defense_counts[first_defense] = 1;
    for (int i = 0; i < m; ++i) row_sums[i] = payoff2(attackers[i], first_defense);

    for (int t = 0; t < rounds; ++t) {
        const int row = static_cast<int>(std::max_element(row_sums.begin(), row_sums.end())
                                         - row_sums.begin());
        auto [defense, score_numerator] = best_defense(hist);
        (void)score_numerator;
        ++row_counts[row];
        for (int c = 0; c < 5; ++c) ++hist[c][attackers[row][c]];
        ++defense_counts[defense];
        for (int i = 0; i < m; ++i) row_sums[i] += payoff2(attackers[i], defense);
    }

    std::int64_t row_total = 0;
    for (auto count : row_counts) row_total += count;
    std::int64_t defense_total = 0;
    for (const auto& entry : defense_counts) defense_total += entry.second;
    const auto max_sum = *std::max_element(row_sums.begin(), row_sums.end());
    const auto [last_best_defense, defender_score_numerator] = best_defense(hist);
    (void)last_best_defense;
    const long double upper = static_cast<long double>(max_sum) / (2 * defense_total);
    const long double lower = 15.0L - static_cast<long double>(defender_score_numerator)
                                            / (2 * row_total);
    std::cout << std::setprecision(18) << upper << '\t' << lower << '\t'
              << defense_counts.size() << '\n';
    for (const auto& [action, count] : defense_counts) {
        for (int c = 0; c < 5; ++c) std::cout << action[c] << (c == 4 ? '\t' : ' ');
        std::cout << count << '\n';
    }
}
