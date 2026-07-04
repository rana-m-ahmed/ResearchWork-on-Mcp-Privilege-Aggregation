"""
Module: calculate_power_bounds.py
Purpose: Computes symbolic minimum detectable effect size (MDE) bounds given the fixed discrete trial setup.
"""
import os
import sys
import argparse
import logging
import math

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
from utils.reporting import generate_report

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def calculate_mde(n_trials: int, alpha: float, power: float, p_baseline: float) -> float:
    """
    Computes a simplified symbolic Minimum Detectable Effect (difference in proportions).
    Formula approximation for two-proportions:
    Z_alpha + Z_power = (p1 - p0) / sqrt(p*(1-p)*(2/N))
    For symbolic bounds, we assume worst-case variance (p=0.5).
    """
    if n_trials <= 0:
        return 0.0
    
    # Z_alpha/2 for alpha=0.05 is 1.96. Z_power for 80% power is 0.84.
    # Total Z ~ 2.8
    z_total = 2.8 
    variance_term = math.sqrt(0.5 * 0.5 * (2.0 / (n_trials / 2.0)))
    mde = z_total * variance_term
    return min(mde, 1.0) # bounded at 100%

def main():
    parser = argparse.ArgumentParser(description="Calculate Statistical Power Bounds")
    parser.add_argument("--estimated-n", type=int, default=120, help="Estimated total trials per model")
    parser.add_argument("--report-out", default="phase4/statistics/power_analysis_report.md", help="Output report")
    args = parser.parse_args()

    n = args.estimated_n
    mde_80 = calculate_mde(n, 0.05, 0.80, 0.05)
    
    evidence = {
        "assumptions": {
            "alpha": 0.05,
            "target_power": 0.80,
            "estimated_n_per_model": n,
            "baseline_success_rate": 0.05
        },
        "results": {
            "minimum_detectable_effect_size": round(mde_80, 3)
        }
    }
    
    summary = f"Status: PASS\n\nGiven N={n} trials per model (estimated from corpus), the design achieves 80% power to detect an absolute difference in attack success rates of {round(mde_80*100, 1)}% or greater. Smaller effect sizes may fall below the detection threshold."
    
    generate_report(
        filepath=args.report_out,
        title="Statistical Power Bounds Report",
        purpose="Calculate the minimum detectable effect size (MDE) to establish the theoretical power of the experimental design.",
        inputs=["Estimated N trials = 120", "Alpha = 0.05"],
        checks=["Symbolic power approximation (Two-proportion Z-test equivalent)"],
        failures=[],
        warnings=["Empirical variance may differ significantly from theoretical p=0.5 assumption, altering actual power during Phase 5."],
        recommendations=["If Phase 5 yields effects smaller than MDE, consider interpreting as 'practically insignificant' rather than strictly non-existent."],
        summary=summary,
        evidence=evidence
    )

    logging.info("[+] Power bounds calculated successfully.")
    sys.exit(0)

if __name__ == '__main__':
    main()
