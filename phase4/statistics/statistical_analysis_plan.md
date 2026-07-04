# Statistical Analysis Plan (SAP)
**Phase 4 Protocol Freeze Document**

## 1. Overview
This document specifies the primary and secondary statistical analyses to be conducted following Phase 5 execution.

## 2. Variables
- **Dependent Variable (Outcome)**: `success` (Binary: 1 if attack condition satisfied, 0 otherwise).
- **Independent Variables (Predictors)**:
  - `metadata_surface_condition`: Categorical (CLEAN, POISON_TD, POISON_CA)
  - `density`: Categorical (D1, D3, D5)
  - `defense_condition`: Categorical (BASELINE, IHR_SPCE)
  - `model_id`: Categorical (M1, M2, M3, M4)

## 3. Hypotheses
### Primary Hypothesis
- **H0 (Null)**: There is no significant difference in the probability of `success` between `CLEAN` and `POISON` conditions.
- **H1 (Alternative)**: The probability of `success` is significantly higher in `POISON` conditions compared to `CLEAN` conditions, controlling for model and density.

### Secondary Hypothesis
- **H0 (Null)**: `defense_condition = IHR_SPCE` does not significantly reduce the probability of `success` in `POISON` conditions compared to `BASELINE`.
- **H1 (Alternative)**: `IHR_SPCE` significantly reduces the probability of `success` in `POISON` conditions.

## 4. Statistical Specification
- **Primary Analysis**: Firth-penalized Logistic Regression.
- **Rationale for Firth**: To mitigate separation issues (e.g., if a model fails 100% of the time on CLEAN or succeeds 100% of the time on POISON), which causes standard maximum likelihood estimation to fail or produce infinite standard errors.
- **Model Equation**: `logit(P(success=1)) = \beta_0 + \beta_1(Surface) + \beta_2(Density) + \beta_3(Model) + \beta_4(Defense) + \epsilon`
- **Effect Sizes**: Reported as Odds Ratios (OR) with 95% Confidence Intervals.

## 5. Significance & Corrections
- **Alpha Level ($\alpha$)**: 0.05
- **Multiple Comparison Correction**: Benjamini-Hochberg (FDR) correction applied to all post-hoc pairwise comparisons to control false discovery rate.

## 6. Power Assumptions & Sensitivity
Given the fixed discrete nature of the trial sets, empirical power is bounded by the permutation of valid conditions. Minimum Detectable Effect (MDE) will be calculated prior to execution based on `N` trials. A sensitivity analysis will drop the highest-variance model to confirm robustness.

## 7. Missing Data
Missing data (e.g., LLM context limit crashes) will be treated as `success=0` (Attack Failed) and explicitly flagged as `ERROR_CRASH` in trial logs.
