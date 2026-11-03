// Fictitious play for a small zero-sum matrix of head-to-head allocations.
// Payoffs are twice castle points, hence exact integers.
// Input: row_count column_count rounds, then row allocations, then column allocations.
// Output: duality gap in points followed by column-strategy probabilities.
#include <algorithm>
#include <array>
#include <iomanip>
#include <iostream>
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

int main() {
    int m, n, rounds;
    if (!(std::cin >> m >> n >> rounds) || m <= 0 || n <= 0 || rounds <= 0) {
        std::cerr << "expected positive row count, column count, and rounds\n";
        return 2;
    }
    std::vector<Allocation> rows(m), columns(n);
    for (auto& action : rows) {
        int sum = 0;
        for (int& x : action) { std::cin >> x; sum += x; }
        if (sum != 100) { std::cerr << "invalid row allocation\n"; return 2; }
    }
    for (auto& action : columns) {
        int sum = 0;
        for (int& x : action) { std::cin >> x; sum += x; }
        if (sum != 100) { std::cerr << "invalid column allocation\n"; return 2; }
    }

    std::vector<std::vector<int>> matrix(m, std::vector<int>(n));
    for (int i = 0; i < m; ++i)
        for (int j = 0; j < n; ++j)
            matrix[i][j] = payoff2(rows[i], columns[j]);

    std::vector<long long> row_counts(m), column_counts(n);
    std::vector<long long> row_sums(m), column_sums(n);
    for (int t = 0; t < rounds; ++t) {
        const int i = static_cast<int>(std::max_element(row_sums.begin(), row_sums.end())
                                      - row_sums.begin());
        const int j = static_cast<int>(std::min_element(column_sums.begin(), column_sums.end())
                                      - column_sums.begin());
        ++row_counts[i];
        ++column_counts[j];
        for (int r = 0; r < m; ++r) row_sums[r] += matrix[r][j];
        for (int c = 0; c < n; ++c) column_sums[c] += matrix[i][c];
    }

    const auto upper = *std::max_element(row_sums.begin(), row_sums.end());
    const auto lower = *std::min_element(column_sums.begin(), column_sums.end());
    std::cout << std::setprecision(17)
              << static_cast<double>(upper - lower) / (2.0 * rounds);
    for (int j = 0; j < n; ++j)
        std::cout << '\t' << static_cast<double>(column_counts[j]) / rounds;
    std::cout << '\n';
}
