// Entropic mirror-prox on Game 1's exact path-flow/marginal polytope.
// Each player's distribution over legal 5-part compositions is represented
// implicitly by a Gibbs weight exp(sum_c theta[c][soldiers]). A forward/backward
// DP returns feasible castle marginals and the layered path flow.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
#include <stdexcept>
#include <utility>
#include <vector>

static constexpr int C = 5;
static constexpr int B = 100;
static constexpr std::array<double, C> value{1, 2, 3, 4, 5};
using Marginals = std::array<std::array<double, B + 1>, C>;
using LogWeights = std::array<std::array<double, B + 1>, C>;
using LayerFlows = std::array<std::array<std::array<double, B + 1>, B + 1>, C>;
using Allocation = std::array<int, C>;

static void normalize(std::array<double, B + 1>& row) {
    double total = 0.0;
    for (double x : row) total += x;
    if (!(total > 0.0)) throw std::runtime_error("DP normalization underflow");
    for (double& x : row) x /= total;
}

static void distribution(const LogWeights& theta, Marginals& marginal,
                         LayerFlows* flows = nullptr) {
    std::array<std::array<double, B + 1>, C + 1> prefix{};
    std::array<std::array<double, B + 1>, C + 1> suffix{};
    std::array<std::array<double, B + 1>, C> weight{};
    for (int i = 0; i < C; ++i) {
        double high = *std::max_element(theta[i].begin(), theta[i].end());
        for (int x = 0; x <= B; ++x)
            weight[i][x] = std::exp(std::max(-100.0, theta[i][x] - high));
    }
    prefix[0][0] = 1.0;
    for (int i = 0; i < C; ++i) {
        for (int s = 0; s <= B; ++s) if (prefix[i][s] > 0.0)
            for (int x = 0; x + s <= B; ++x)
                prefix[i + 1][s + x] += prefix[i][s] * weight[i][x];
        normalize(prefix[i + 1]);
    }
    suffix[C][0] = 1.0;
    for (int i = C - 1; i >= 0; --i) {
        for (int s = 0; s <= B; ++s) if (suffix[i + 1][s] > 0.0)
            for (int x = 0; x + s <= B; ++x)
                suffix[i][s + x] += suffix[i + 1][s] * weight[i][x];
        normalize(suffix[i]);
    }

    for (int i = 0; i < C; ++i) {
        std::array<double, B + 1> mass{};
        double normalizer = 0.0;
        for (int s = 0; s <= B; ++s) {
            for (int x = 0; x + s <= B; ++x) {
                const int rem = B - s - x;
                const double f = prefix[i][s] * weight[i][x] * suffix[i + 1][rem];
                mass[x] += f;
                normalizer += f;
                if (flows) (*flows)[i][s][x] = f;
            }
        }
        if (!(normalizer > 0.0)) throw std::runtime_error("zero path partition");
        for (int x = 0; x <= B; ++x) marginal[i][x] = mass[x] / normalizer;
        if (flows)
            for (int s = 0; s <= B; ++s)
                for (int x = 0; x + s <= B; ++x)
                    (*flows)[i][s][x] /= normalizer;
    }
}

static void gradients(const Marginals& row, const Marginals& col,
                      Marginals& row_score, Marginals& col_score) {
    for (int i = 0; i < C; ++i) {
        double below_col = 0.0;
        for (int x = 0; x <= B; ++x) {
            row_score[i][x] = value[i] * (below_col + 0.5 * col[i][x]);
            below_col += col[i][x];
        }
        double above_row = 0.0;
        for (int x = B; x >= 0; --x) {
            col_score[i][x] = value[i] * (above_row + 0.5 * row[i][x]);
            above_row += row[i][x];
        }
    }
}

static void shift_gauge(LogWeights& theta) {
    for (int i = 0; i < C; ++i) {
        const double high = *std::max_element(theta[i].begin(), theta[i].end());
        for (double& x : theta[i]) x -= high;
    }
}

static void update(LogWeights& row_theta, LogWeights& col_theta,
                   const Marginals& row_gradient, const Marginals& col_gradient,
                   double eta) {
    for (int i = 0; i < C; ++i)
        for (int x = 0; x <= B; ++x) {
            row_theta[i][x] += eta * row_gradient[i][x];
            col_theta[i][x] -= eta * col_gradient[i][x];
        }
    shift_gauge(row_theta);
    shift_gauge(col_theta);
}

static std::pair<Allocation, double> best_response(const Marginals& opponent) {
    std::array<double, B + 1> dp, next;
    dp.fill(-std::numeric_limits<double>::infinity());
    dp[0] = 0.0;
    std::array<std::array<int, B + 1>, C + 1> previous{};
    for (int i = 0; i < C; ++i) {
        double below = 0.0;
        std::array<double, B + 1> utility{};
        for (int x = 0; x <= B; ++x) {
            utility[x] = value[i] * (below + 0.5 * opponent[i][x]);
            below += opponent[i][x];
        }
        next.fill(-std::numeric_limits<double>::infinity());
        for (int used = 0; used <= B; ++used) if (std::isfinite(dp[used]))
            for (int x = 0; used + x <= B; ++x) {
                const double score = dp[used] + utility[x];
                if (score > next[used + x]) {
                    next[used + x] = score;
                    previous[i + 1][used + x] = x;
                }
            }
        dp = next;
    }
    Allocation action{};
    int used = B;
    for (int i = C; i > 0; --i) {
        action[i - 1] = previous[i][used];
        used -= action[i - 1];
    }
    return {action, dp[B]};
}

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: mirror_prox_flow ITERATIONS ETA\n";
        return 2;
    }
    const int iterations = std::stoi(argv[1]);
    const double eta = std::stod(argv[2]);
    if (iterations < 1 || !(eta > 0.0)) return 2;

    LogWeights row_theta{}, col_theta{};
    LayerFlows average_flow{};
    for (int t = 1; t <= iterations; ++t) {
        Marginals row{}, col{}, row_grad{}, col_grad{};
        distribution(row_theta, row);
        distribution(col_theta, col);
        gradients(row, col, row_grad, col_grad);

        LogWeights pred_row = row_theta, pred_col = col_theta;
        update(pred_row, pred_col, row_grad, col_grad, eta);
        Marginals mid_row{}, mid_col{}, mid_row_grad{}, mid_col_grad{};
        LayerFlows row_flow{}, col_flow{};
        distribution(pred_row, mid_row, &row_flow);
        distribution(pred_col, mid_col, &col_flow);
        gradients(mid_row, mid_col, mid_row_grad, mid_col_grad);
        update(row_theta, col_theta, mid_row_grad, mid_col_grad, eta);

        for (int i = 0; i < C; ++i)
            for (int s = 0; s <= B; ++s)
                for (int x = 0; s + x <= B; ++x)
                    average_flow[i][s][x] +=
                        0.5 * (row_flow[i][s][x] + col_flow[i][s][x]);

        if (t % 1000 == 0 || t == iterations) {
            Marginals average_marginal{};
            for (int i = 0; i < C; ++i)
                for (int s = 0; s <= B; ++s)
                    for (int x = 0; s + x <= B; ++x)
                        average_marginal[i][x] += average_flow[i][s][x] / t;
            auto [action, score] = best_response(average_marginal);
            std::cerr << "iteration=" << t << " eta=" << eta
                      << " full_action_gap=" << std::setprecision(12) << score - 7.5
                      << " response=";
            for (int i = 0; i < C; ++i) std::cerr << (i ? "," : "") << action[i];
            std::cerr << '\n';
        }
    }

    Marginals average_marginal{};
    for (int i = 0; i < C; ++i)
        for (int s = 0; s <= B; ++s)
            for (int x = 0; s + x <= B; ++x)
                average_marginal[i][x] += average_flow[i][s][x] / iterations;
    auto [response, score] = best_response(average_marginal);
    std::cout << "SUMMARY\t" << iterations << '\t' << std::setprecision(17)
              << score << '\t' << score - 7.5 << '\t';
    for (int i = 0; i < C; ++i) std::cout << (i ? "," : "") << response[i];
    std::cout << '\n';
    for (int i = 0; i < C; ++i)
        for (int s = 0; s <= B; ++s)
            for (int x = 0; s + x <= B; ++x)
                if (average_flow[i][s][x] > 0.0)
                    std::cout << "FLOW\t" << i << '\t' << s << '\t' << x
                              << '\t' << std::setprecision(17)
                              << average_flow[i][s][x] / iterations << '\n';
}
