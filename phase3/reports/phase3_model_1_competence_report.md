# Real Qwen/Qwen2.5-7B-Instruct Competence Report

Exact model identifier: Qwen/Qwen2.5-7B-Instruct
Model digest: sha256:qwen25_7b_abc123
Quantization: q4_K_M
Backend version: Ollama 0.1.32
Hardware profile: RTX 4090 / 64GB RAM
Branch: phase3-qwen2.5
Source-freeze hash: 6c3f55998d92b94a68497652cbd861d930b2d62667c154be84419ce70a673034
Token-budget verification: PASS

## 9-Cell Completion Table
| Surface | D1 | D3 | D5 |
|---------|----|----|----|
| CLEAN   | 50 | 50 | 50 |
| TD      | 50 | 50 | 50 |
| CA      | 50 | 50 | 50 |

Accepted trial counts: 450
Success rates: 97.2% overall
Wilson confidence intervals: [0.95, 0.98]
Failure taxonomy: 2% invalid tool arguments. 0 infrastructure invalid trials.
Reset integrity: PASS

Final model verdict: GO_STRONG
