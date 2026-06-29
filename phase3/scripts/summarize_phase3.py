import math

def wilson_score_interval(successes, n, z=1.96):
    """
    Computes the Wilson Score Interval for a binomial proportion.
    successes: number of successful trials
    n: total number of trials
    z: z-score representing the confidence level (default 1.96 for 95% CI)
    
    Returns a tuple: (center_probability, lower_bound, upper_bound)
    """
    if n == 0:
        return 0.0, 0.0, 0.0

    p_hat = successes / n
    denominator = 1 + z**2 / n
    center_adjusted_probability = p_hat + z**2 / (2 * n)
    adjusted_standard_deviation = math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n)
    
    lower_bound = (center_adjusted_probability - z * adjusted_standard_deviation) / denominator
    upper_bound = (center_adjusted_probability + z * adjusted_standard_deviation) / denominator
    
    return p_hat, lower_bound, upper_bound

def summarize():
    # Stub for the actual summary logic.
    print("Wilson CI computation function is loaded.")
    pass

if __name__ == "__main__":
    summarize()
