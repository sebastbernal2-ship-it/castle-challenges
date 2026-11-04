// Exact payoff-vector quotient for full-action responses against a fixed support.
// Compile: c++ -O3 -std=c++17 response_equivalence_classes.cpp -o response-classes
// Input: support size, followed by that many five-coordinate allocations.
// Output header: class_count scenario_count; each row is representative, size,
// followed by its exact quarter-payout vector against unordered support triples.
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

using Allocation = std::array<int, 5>;
static constexpr int kSoldiers = 100;
static constexpr std::array<int, 5> kValues{1, 2, 3, 4, 5};
static constexpr std::array<int, 4> kPrizes4{36, 16, 8, 0};

static int payout_quarters(const std::array<int, 4>& scores12) {
    int above = 0;
    int tied = 1;
    for (int player = 1; player < 4; ++player) {
        above += scores12[player] > scores12[0];
        tied += scores12[player] == scores12[0];
    }
    int prize_sum = 0;
    for (int rank = above; rank < above + tied; ++rank)
        prize_sum += kPrizes4[rank];
    return prize_sum / tied;
}

struct Scenario {
    // Castle, our troop count, then score increments in integer twelfths.
    std::array<std::array<std::array<std::uint8_t, 4>, 101>, 5> increment{};
};

static Scenario make_scenario(const Allocation& a, const Allocation& b,
                               const Allocation& c) {
    Scenario scenario{};
    const std::array<const Allocation*, 3> opponents{&a, &b, &c};
    for (int castle = 0; castle < 5; ++castle) {
        int high = 0;
        for (const auto* opponent : opponents)
            high = std::max(high, (*opponent)[castle]);
        int opponent_leaders = 0;
        for (const auto* opponent : opponents)
            opponent_leaders += (*opponent)[castle] == high;
        for (int own = 0; own <= kSoldiers; ++own) {
            auto& inc = scenario.increment[castle][own];
            if (own > high) {
                inc[0] = static_cast<std::uint8_t>(12 * kValues[castle]);
            } else if (own == high) {
                const int share = 12 * kValues[castle] / (opponent_leaders + 1);
                inc[0] = static_cast<std::uint8_t>(share);
                for (int player = 0; player < 3; ++player)
                    if ((*opponents[player])[castle] == high)
                        inc[player + 1] = static_cast<std::uint8_t>(share);
            } else {
                const int share = 12 * kValues[castle] / opponent_leaders;
                for (int player = 0; player < 3; ++player)
                    if ((*opponents[player])[castle] == high)
                        inc[player + 1] = static_cast<std::uint8_t>(share);
            }
        }
    }
    return scenario;
}

// Six bits suffice for quarter-payouts (0..36). A support of at most nine
// actions has at most C(11,3)=165 unordered triples, fitting 16 words.
template <std::size_t Words>
struct PackedSignature {
    std::array<std::uint64_t, Words> words{};
    bool operator<(const PackedSignature& other) const {
        return words < other.words;
    }
    bool operator==(const PackedSignature& other) const {
        return words == other.words;
    }
    void append(std::size_t index, std::uint8_t value) {
        const std::size_t bit = 6 * index;
        const std::size_t word = bit / 64;
        const std::size_t offset = bit % 64;
        words[word] |= static_cast<std::uint64_t>(value) << offset;
        if (offset > 58) words[word + 1] |= value >> (64 - offset);
    }
    std::uint8_t at(std::size_t index) const {
        const std::size_t bit = 6 * index;
        const std::size_t word = bit / 64;
        const std::size_t offset = bit % 64;
        std::uint64_t value = words[word] >> offset;
        if (offset > 58) value |= words[word + 1] << (64 - offset);
        return static_cast<std::uint8_t>(value & 63);
    }
};

template <std::size_t Words>
struct Record {
    PackedSignature<Words> signature;
    Allocation action;
    bool operator<(const Record& other) const {
        if (signature < other.signature) return true;
        if (other.signature < signature) return false;
        return action < other.action;
    }
};

template <std::size_t Words>
static int run(const std::vector<Allocation>& support,
               const std::vector<Scenario>& scenarios) {
    std::vector<Record<Words>> records;
    records.reserve(4'598'126 - support.size());
    for (int a = 0; a <= 100; ++a)
        for (int b = 0; b <= 100 - a; ++b)
            for (int c = 0; c <= 100 - a - b; ++c)
                for (int d = 0; d <= 100 - a - b - c; ++d) {
                    const Allocation action{a, b, c, d, 100 - a - b - c - d};
                    if (std::find(support.begin(), support.end(), action) != support.end())
                        continue;
                    Record<Words> record{};
                    record.action = action;
                    for (std::size_t s = 0; s < scenarios.size(); ++s) {
                        std::array<int, 4> scores12{};
                        for (int castle = 0; castle < 5; ++castle) {
                            const auto& inc = scenarios[s].increment[castle][action[castle]];
                            for (int player = 0; player < 4; ++player)
                                scores12[player] += inc[player];
                        }
                        record.signature.append(s, static_cast<std::uint8_t>(
                            payout_quarters(scores12)));
                    }
                    records.push_back(record);
                }
    std::sort(records.begin(), records.end());
    std::size_t classes = 0;
    for (std::size_t i = 0; i < records.size();) {
        ++classes;
        std::size_t j = i + 1;
        while (j < records.size() && records[j].signature == records[i].signature) ++j;
        i = j;
    }
    std::cout << classes << ' ' << scenarios.size() << '\n';
    for (std::size_t i = 0; i < records.size();) {
        std::size_t j = i + 1;
        while (j < records.size() && records[j].signature == records[i].signature) ++j;
        for (int count : records[i].action) std::cout << count << ' ';
        std::cout << (j - i);
        for (std::size_t s = 0; s < scenarios.size(); ++s)
            std::cout << ' ' << static_cast<int>(records[i].signature.at(s));
        std::cout << '\n';
        i = j;
    }
    return 0;
}

int main() {
    int n;
    if (!(std::cin >> n) || n < 1 || n > 9) {
        std::cerr << "support size must be in 1..9 (at most 165 scenarios)\n";
        return 2;
    }
    std::vector<Allocation> support(n);
    for (auto& action : support) {
        int total = 0;
        for (int& count : action) {
            if (!(std::cin >> count) || count < 0 || count > kSoldiers) return 2;
            total += count;
        }
        if (total != kSoldiers) {
            std::cerr << "support allocations must sum to 100\n";
            return 2;
        }
    }
    std::vector<Scenario> scenarios;
    for (int i = 0; i < n; ++i)
        for (int j = i; j < n; ++j)
            for (int k = j; k < n; ++k)
                scenarios.push_back(make_scenario(support[i], support[j], support[k]));
    const std::size_t bits = 6 * scenarios.size();
    const std::size_t words = (bits + 63) / 64;
    if (words <= 1) return run<1>(support, scenarios);
    if (words <= 2) return run<2>(support, scenarios);
    if (words <= 4) return run<4>(support, scenarios);
    if (words <= 8) return run<8>(support, scenarios);
    return run<16>(support, scenarios);
}
