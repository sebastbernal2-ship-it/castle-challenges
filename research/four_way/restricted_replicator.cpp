// Native finite-support multiplicative-weights solver for the four-player game.
// Input: support size, iterations, eta, then one 100-soldier allocation per row.
// Output: final and second-half average probabilities as JSON arrays.
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <vector>

using Allocation = std::array<int, 5>;
static constexpr std::array<int, 5> value{1, 2, 3, 4, 5};
static constexpr std::array<int, 4> prize4{36, 16, 8, 0};

static std::array<int, 4> payout4(const Allocation& a, const Allocation& b,
                                   const Allocation& c, const Allocation& d) {
    const std::array<const Allocation*, 4> players{&a, &b, &c, &d};
    std::array<int, 4> scores{};
    for (int castle = 0; castle < 5; ++castle) {
        int high = 0;
        for (auto p : players) high = std::max(high, (*p)[castle]);
        int leaders = 0;
        for (auto p : players) leaders += ((*p)[castle] == high);
        const int share = value[castle] * (12 / leaders);
        for (int player = 0; player < 4; ++player)
            if ((*players[player])[castle] == high) scores[player] += share;
    }
    std::array<int, 4> order{0, 1, 2, 3};
    std::sort(order.begin(), order.end(), [&](int x, int y) {
        return scores[x] > scores[y];
    });
    std::array<int, 4> result{};
    for (int start = 0; start < 4;) {
        int end = start + 1;
        while (end < 4 && scores[order[end]] == scores[order[start]]) ++end;
        int sum = 0;
        for (int rank = start; rank < end; ++rank) sum += prize4[rank];
        const int shared = sum / (end - start);
        for (int rank = start; rank < end; ++rank) result[order[rank]] = shared;
        start = end;
    }
    return result;
}

struct Triple { int j, k, l, multiplicity; };

int main() {
    int n, iterations;
    long double eta;
    if (!(std::cin >> n >> iterations >> eta) || n <= 0 || iterations <= 0 || eta <= 0) {
        std::cerr << "expected positive support size, iteration count, and eta\n";
        return 2;
    }
    std::vector<Allocation> actions(n);
    for (auto& action : actions) {
        int sum = 0;
        for (int& x : action) { std::cin >> x; sum += x; }
        if (sum != 100) { std::cerr << "invalid allocation\n"; return 2; }
    }

    std::vector<Triple> triples;
    for (int j = 0; j < n; ++j)
        for (int k = j; k < n; ++k)
            for (int l = k; l < n; ++l) {
                const int mult = (j == l) ? 1 : (j == k || k == l) ? 3 : 6;
                triples.push_back({j, k, l, mult});
            }

    // Payoff is stored in exact quarter-points, matching the tournament rule.
    std::vector<std::vector<int>> payoff(n, std::vector<int>(triples.size()));
    for (int i = 0; i < n; ++i)
        for (size_t t = 0; t < triples.size(); ++t) {
            const auto& tr = triples[t];
            payoff[i][t] = payout4(actions[i], actions[tr.j], actions[tr.k],
                                   actions[tr.l])[0];
        }

    std::vector<long double> p(n, 1.0L / n), average(n, 0.0L);
    int kept = 0;
    for (int step = 0; step < iterations; ++step) {
        std::vector<long double> utility(n, 0.0L);
        for (size_t t = 0; t < triples.size(); ++t) {
            const auto& tr = triples[t];
            const long double mass = tr.multiplicity * p[tr.j] * p[tr.k] * p[tr.l];
            if (mass == 0) continue;
            for (int i = 0; i < n; ++i)
                utility[i] += mass * payoff[i][t] / 4.0L;
        }
        std::vector<long double> logits(n);
        long double top = -1e100L;
        for (int i = 0; i < n; ++i) {
            logits[i] = std::log(std::max(p[i], 1e-300L)) + eta * (utility[i] - 3.75L);
            top = std::max(top, logits[i]);
        }
        long double norm = 0;
        for (auto& x : logits) { x = std::exp(x - top); norm += x; }
        for (int i = 0; i < n; ++i) p[i] = logits[i] / norm;
        if (step >= iterations / 2) {
            for (int i = 0; i < n; ++i) average[i] += p[i];
            ++kept;
        }
    }
    for (auto& x : average) x /= kept;
    std::cout << std::setprecision(21) << "{\n  \"final_probabilities\": [";
    for (int i = 0; i < n; ++i) std::cout << (i ? ", " : "") << p[i];
    std::cout << "],\n  \"last_half_time_average_probabilities\": [";
    for (int i = 0; i < n; ++i) std::cout << (i ? ", " : "") << average[i];
    std::cout << "]\n}\n";
}
