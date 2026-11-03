// Optional compiled max-plus DP kernel for the exact Game 1 best-response oracle.
#include <algorithm>
#include <cmath>
#include <limits>
#include <cstdint>

extern "C" void castle_h2h_dp(const double* tables, int soldiers,
                                double* out_value, int* out_allocation) {
    constexpr int MAX_SOLDIERS = 100;
    constexpr int CASTLES = 5;
    double dp[CASTLES + 1][MAX_SOLDIERS + 1];
    int choice[CASTLES + 1][MAX_SOLDIERS + 1]{};
    for (int i = 0; i <= CASTLES; ++i)
        for (int t = 0; t <= soldiers; ++t)
            dp[i][t] = -std::numeric_limits<double>::infinity();
    dp[0][0] = 0.0;
    for (int i = 1; i <= CASTLES; ++i) {
        const double* row = tables + (i - 1) * (MAX_SOLDIERS + 1);
        for (int used = 0; used <= soldiers; ++used) {
            for (int x = 0; x <= used; ++x) {
                const double candidate = dp[i - 1][used - x] + row[x];
                if (candidate > dp[i][used]) {
                    dp[i][used] = candidate;
                    choice[i][used] = x;
                }
            }
        }
    }
    int remaining = soldiers;
    for (int i = CASTLES; i >= 1; --i) {
        out_allocation[i - 1] = choice[i][remaining];
        remaining -= out_allocation[i - 1];
    }
    *out_value = dp[CASTLES][soldiers];
}

extern "C" void castle_h2h_dp_counts(const std::int64_t* counts, int soldiers,
                                       std::int64_t* out_numerator,
                                       int* out_allocation) {
    constexpr int MAX_SOLDIERS = 100;
    constexpr int CASTLES = 5;
    constexpr std::int64_t NEG = std::numeric_limits<std::int64_t>::min() / 4;
    std::int64_t dp[CASTLES + 1][MAX_SOLDIERS + 1];
    std::int64_t q[CASTLES][MAX_SOLDIERS + 1];
    int choice[CASTLES + 1][MAX_SOLDIERS + 1]{};
    for (int castle = 0; castle < CASTLES; ++castle) {
        std::int64_t cumulative = 0;
        const std::int64_t total = [&]() {
            std::int64_t sum = 0;
            for (int x = 0; x <= soldiers; ++x)
                sum += counts[castle * (MAX_SOLDIERS + 1) + x];
            return sum;
        }();
        for (int x = 0; x <= soldiers; ++x) {
            const std::int64_t mass = counts[castle * (MAX_SOLDIERS + 1) + x];
            q[castle][x] = (castle + 1) * (2 * cumulative + mass);
            cumulative += mass;
        }
        if (total <= 0) { *out_numerator = 0; return; }
    }
    for (int i = 0; i <= CASTLES; ++i)
        for (int t = 0; t <= soldiers; ++t)
            dp[i][t] = NEG;
    dp[0][0] = 0;
    for (int i = 1; i <= CASTLES; ++i) {
        for (int used = 0; used <= soldiers; ++used) {
            for (int x = 0; x <= used; ++x) {
                const std::int64_t candidate = dp[i - 1][used - x] + q[i - 1][x];
                if (candidate > dp[i][used]) {
                    dp[i][used] = candidate;
                    choice[i][used] = x;
                }
            }
        }
    }
    int remaining = soldiers;
    for (int i = CASTLES; i >= 1; --i) {
        out_allocation[i - 1] = choice[i][remaining];
        remaining -= out_allocation[i - 1];
    }
    *out_numerator = dp[CASTLES][soldiers];
}
