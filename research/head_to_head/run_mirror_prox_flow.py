#!/usr/bin/env python3
"""Run entropic mirror-prox on the Game 1 path-flow strategy polytope.

The C++ kernel returns an averaged feasible path flow. A deterministic flow
path-decomposition and largest-remainder rounding turn it into an explicit
finite mixture, which is then suitable for the exact integer-DP verifier.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def decompose_flow(flow: dict[tuple[int, int], list[tuple[int, float]]],
                   *, tolerance: float = 1e-14) -> dict[tuple[int, ...], float]:
    """Decompose a five-layer 0-to-100 flow into legal allocation paths."""
    paths: dict[tuple[int, ...], float] = {}
    for _ in range(100_000):
        result: list[tuple[int, ...]] | None = None

        def visit(layer: int, total: int, path: list[int]) -> list[tuple[int, ...]] | None:
            if layer == 5:
                return [tuple(path)] if total == 100 else None
            choices = sorted(flow.get((layer, total), ()), key=lambda edge: edge[1],
                             reverse=True)
            for soldiers, mass in choices:
                if mass <= tolerance or total + soldiers > 100:
                    continue
                found = visit(layer + 1, total + soldiers, path + [soldiers])
                if found is not None:
                    return found
            return None

        found = visit(0, 0, [])
        if found is None:
            break
        allocation = found[0]
        bottleneck = min(next(mass for soldiers, mass in flow[(layer, sum(allocation[:layer]))]
                              if soldiers == allocation[layer]) for layer in range(5))
        if bottleneck <= tolerance:
            break
        paths[allocation] = paths.get(allocation, 0.0) + bottleneck
        for layer in range(5):
            state = sum(allocation[:layer])
            edges = flow[(layer, state)]
            for index, (soldiers, mass) in enumerate(edges):
                if soldiers == allocation[layer]:
                    edges[index] = (soldiers, max(0.0, mass - bottleneck))
                    break
    total = sum(paths.values())
    if total <= 0:
        raise RuntimeError("could not decompose the averaged path flow")
    if abs(total - 1.0) > 1e-8:
        raise RuntimeError(f"flow decomposition left mass {1.0-total:.3g}")
    return {action: mass / total for action, mass in paths.items()}


def quantize(probabilities: dict[tuple[int, ...], float], total: int
             ) -> dict[tuple[int, ...], int]:
    mass = sum(probabilities.values())
    scaled = {action: probability * total / mass
              for action, probability in probabilities.items()}
    counts = {action: int(value) for action, value in scaled.items()}
    residual = total - sum(counts.values())
    order = sorted(scaled, key=lambda action: scaled[action] - counts[action],
                   reverse=True)
    for action in order[:residual]:
        counts[action] += 1
    return {action: count for action, count in counts.items() if count}


def run(iterations: int, eta: float, frequency_total: int) -> dict:
    compiler = shutil.which("c++")
    if compiler is None:
        raise RuntimeError("a C++17 compiler is required")
    source = Path(__file__).with_name("mirror_prox_flow.cpp")
    with tempfile.TemporaryDirectory(prefix="h2h-mirror-prox-") as directory:
        binary = Path(directory) / "mirror_prox_flow"
        subprocess.run([compiler, "-O3", "-std=c++17", str(source), "-o", str(binary)],
                       check=True, stdout=subprocess.DEVNULL)
        try:
            completed = subprocess.run([str(binary), str(iterations), str(eta)],
                                       text=True, capture_output=True, check=True)
        except subprocess.CalledProcessError as error:
            raise RuntimeError(error.stderr or str(error)) from error
    flow: dict[tuple[int, int], list[tuple[int, float]]] = {}
    summary = None
    for line in completed.stdout.splitlines():
        fields = line.split("\t")
        if fields[0] == "SUMMARY":
            summary = {
                "iterations": int(fields[1]),
                "continuous_best_response_score": float(fields[2]),
                "continuous_gap": float(fields[3]),
                "continuous_best_response": list(map(int, fields[4].split(","))),
            }
        elif fields[0] == "FLOW":
            layer, state, soldiers = map(int, fields[1:4])
            flow.setdefault((layer, state), []).append((soldiers, float(fields[4])))
    if summary is None:
        raise RuntimeError("mirror-prox kernel emitted no summary")
    distribution = decompose_flow(flow)
    counts = quantize(distribution, frequency_total)
    strategy = [[list(action), count / frequency_total]
                for action, count in sorted(counts.items())]
    return {
        "source": "research/head_to_head/mirror_prox_flow.cpp",
        "method": "entropic mirror-prox over the layered path-flow polytope; averaged row/column flows",
        "frequency_total": frequency_total,
        **summary,
        "flow_decomposition_support": len(distribution),
        "quantized_support": len(counts),
        "iteration_log": completed.stderr.splitlines(),
        "strategy": strategy,
        "warning": "The flow solver is floating-point candidate generation; only verify_strategy.py's exact integer-DP audit certifies the quantized mixture.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--eta", type=float, default=0.05)
    parser.add_argument("--frequency-total", type=int, default=20_000_260)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.iterations, args.eta, args.frequency_total)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "strategy"},
                     indent=2))


if __name__ == "__main__":
    main()
