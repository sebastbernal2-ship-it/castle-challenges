// Native payoff-tensor kernel for the restricted symmetric Game 2 solver.
// Input is a flat n-by-5 allocation array. Output is n-by-C(n+2,3) quarter-points,
// with columns ordered by opponent triples j<=k<=l.
#include <algorithm>
#include <array>
#include <cstdint>
#include <vector>

using Allocation = std::array<int, 5>;
static constexpr std::array<int, 5> value{1, 2, 3, 4, 5};
static constexpr std::array<int, 4> prize4{36, 16, 8, 0};

static std::uint8_t payout_quarters(const Allocation& a, const Allocation& b,
                                    const Allocation& c, const Allocation& d) {
    const std::array<const Allocation*, 4> players{&a, &b, &c, &d};
    std::array<int, 4> scores{};
    for (int castle = 0; castle < 5; ++castle) {
        int high = 0;
        for (const auto* player : players) high = std::max(high, (*player)[castle]);
        int leaders = 0;
        for (const auto* player : players) leaders += ((*player)[castle] == high);
        const int share12 = value[castle] * (12 / leaders);
        for (int p = 0; p < 4; ++p)
            if ((*players[p])[castle] == high) scores[p] += share12;
    }
    int above = 0;
    int tied = 1;
    for (int player = 1; player < 4; ++player) {
        above += scores[player] > scores[0];
        tied += scores[player] == scores[0];
    }
    int prize_sum = 0;
    for (int rank = above; rank < above + tied; ++rank)
        prize_sum += prize4[rank];
    return static_cast<std::uint8_t>(prize_sum / tied);
}

extern "C" void four_way_payoff_tensor(const int* flat_actions, int n,
                                        std::uint8_t* output) {
    std::vector<Allocation> actions(n);
    for (int i = 0; i < n; ++i)
        for (int castle = 0; castle < 5; ++castle)
            actions[i][castle] = flat_actions[5 * i + castle];
    const std::size_t triple_count = static_cast<std::size_t>(n) * (n + 1) * (n + 2) / 6;
    std::size_t triple = 0;
    for (int j = 0; j < n; ++j)
        for (int k = j; k < n; ++k)
            for (int ell = k; ell < n; ++ell, ++triple)
                for (int i = 0; i < n; ++i)
                    output[static_cast<std::size_t>(i) * triple_count + triple] =
                        payout_quarters(actions[i], actions[j], actions[k], actions[ell]);
}
