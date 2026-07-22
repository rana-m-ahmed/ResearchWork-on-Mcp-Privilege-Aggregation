# M2 Final Phase 5.5 Completion-Boundary Remediation

The latest replacement pretrial showed that M2 executed the frozen expected
tool plans correctly once, but then emitted the same calls again instead of a
terminal response. The repeated-call guard prevented the second side effect,
but the attempts were still marked invalid because the loop waited for another
model turn.

M2 now has an additive completion-boundary control. When the executed tool
transcript exactly matches the frozen expected tool plan, the runtime accepts
the completed plan immediately and does not request another model turn. The
boundary is reached only after the exact ordered calls and arguments have been
executed; extra, missing, or unauthorized calls do not qualify.

The control is M2-only. Other model branches retain their existing behavior.

Verification:

- Agent-loop completion and duplicate-call tests: `12 passed`.
- Source-freeze and notebook binding tests: `5 passed`.
- M2 source-freeze source commit: `6b43efce24da2dc9d763535f7b973cabbe30a6a5`.
- M2 branch head: `60173ce3a9441de7e2a0b12ef777e3627199fa7b`.
- Official preflight source matching, synthetic canary, and historical closure
  passed. CUDA availability and official-dispatch authorization remain local
  environment gates.
