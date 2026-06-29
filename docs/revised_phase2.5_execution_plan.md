# **Phase 2.5 Execution Plan — Version 1.3.1**

## **Context Window and Token Budget Profiling**

### **Privilege Aggregation via Metadata Poisoning in Model Context Protocol (MCP) Tool Ecosystems**

**Document Version:** 1.3.1  
**Document Status:** Publication-Grade Methodology — Final Standalone Specification after Micro-Revision  
**Supersedes:** Version 1.0, Version 1.1, Version 1.2, Version 1.3, and all intermediate drafts  
**Document Type:** Phase 2.5 Engineering and Measurement Plan  
**Authority Chain:** Phase 0 Scope Lock Memo $\\rightarrow$ Phase 1 Benchmark/Provenance Governance $\\rightarrow$ Revised Execution Plan $\\rightarrow$ Phase 2 Revised Plan (PHASE2.md) $\\rightarrow$ This Document

## **Micro-Revision Integration Note**

Version 1.3.1 performs a targeted execution-readiness cleanup over Version 1.3. It does not expand the study into Phase 3, Phase 4, or Phase 5. The revision only repairs internal inconsistencies, strengthens tokenizer endpoint authentication, adds explicit reference strings, removes copied citation artifacts, clarifies that placeholder profiling cannot support final GO, and makes the Phase 2.5-to-Phase 3 boundary explicit.

The Phase 2.5 GO gate authorizes only the start of **Phase 3 competence-baseline work**. It does not authorize protocol freeze, adversarial experimentation, ASR/TID calculation, Critical Exploit counting, defense evaluation, or any publication claim.


## **Executive Summary**

Phase 2.5 is a **Context Window and Token Budget Profiling** phase positioned between the Phase 2 infrastructure build and the Phase 3 competence baseline. Its sole purpose is to measure whether each experimental condition — across all nine schema variants — fits within the strict **4,096-token operational ceiling** established in the revised execution plan.  
Phase 2.5 is an **engineering and measurement phase only**. It does not evaluate attack success, compute Attack Success Rate (ASR), measure model robustness, produce security findings, or draw conclusions about privilege aggregation. It produces token-budget evidence, context-window evidence, schema growth evidence, and budget feasibility evidence.  
This standalone specification integrates all hardware-tier adaptations for Tier 3 environments (7.4 GB RAM, integrated graphics) , enforces absolute payload immutability against text encoding manipulation , establishes native Ollama tokenization via /api/tokenize as the authoritative pathway , and introduces strict script-integrity and fake-endpoint blocking controls. The phase concludes with a structured **GO / REVISE** decision gate before Phase 3 competence-baseline work may begin. A GO decision from this document is not permission to start Phase 4 protocol freeze or Phase 5 core adversarial experimentation.

## **Table of Contents**

1. Phase Boundary, Mandate, and Formal Objective  
2. Methodological Assumptions  
3. Frozen Project Context Summary  
4. Mathematical Notation and Operational Ceiling  
5. Token Budget Formula and Justification  
6. Experimental Conditions  
7. Tokenizer Selection, Validation, and Serialization Standards  
8. Local Model Recommendations and Hardware Tiers  
9. Multi-Model Validation Design  
10. Repository Structure and Traceability  
11. Sub-Phase Execution Plan  
12. Token Budget Thresholds and Technical Justification  
13. Deterministic Decision Gate and Pruning Stopping Criteria  
14. Schema Growth Analysis Specification  
15. Researcher Independence and Precision Reconciliation Protocol  
16. Reporting Requirements and Table Templates  
17. Deliverable Specifications and Acceptance Criteria  
18. Phase 3 Readiness Criteria  
19. Threats to Validity  
20. Risk Register  
21. Phase 2.5 Non-Negotiable Rules  
* Appendix A: Input Consumption Map  
* Appendix B: Script Specifications  
* Appendix C: Reproducibility Manifest Template

## **1\. Phase Boundary, Mandate, and Formal Objective**

### **1.1 Formal Mathematical Objective**

Phase 2.5 is modeled as a deterministic measurement pipeline rather than an empirical or stochastic experimental evaluation. Formally, let $\\mathcal{X}$ represent the multi-component prompt space defined by the Cartesian product of the input variables:

$$\\mathcal{X} \= \\mathcal{X}\_{\\text{System}} \\times \\mathcal{X}\_{\\text{Schemas}} \\times \\mathcal{X}\_{\\text{CapAdv}} \\times \\mathcal{X}\_{\\text{Payload}} \\times \\mathcal{X}\_{\\text{Task}} \\times \\mathcal{X}\_{\\text{History}}$$  
Phase 2.5 evaluates a deterministic evaluation mapping $f: \\mathcal{X} \\rightarrow \\mathcal{Y}$, where the output space $\\mathcal{Y}$ is defined as:

$$\\mathcal{Y} \= \\mathbb{N}\_{\\text{Total}} \\times \\mathbb{R}\_{\\text{Utilization}} \\times \\mathcal{C}\_{\\text{Classification}} \\times \\mathcal{D}\_{\\text{Decision}}$$  
The objective variables map directly to system execution constraints:

* $\\mathbb{N}\_{\\text{Total}}$ represents the exact model-native token count of the combined context layout.  
* $\\mathbb{R}\_{\\text{Utilization}}$ represents the exact percentage utilization of the context resource window.  
* $\\mathcal{C}\_{\\text{Classification}} \\in \\{\\text{SAFE}, \\text{WARNING}, \\text{CRITICAL}\\}$ defines the engineering operating region.  
* $\\mathcal{D}\_{\\text{Decision}} \\in \\{\\text{GO}, \\text{REVISE}\\}$ establishes the formal progression vector for the target architecture.

### **1.2 Scope Boundaries**

Phase 2.5 performs the following engineering and measurement activities only:

1. Validates the hardware environment and documents the active model backend mode.  
2. Validates and documents the tokenizer to be used for all profiling, utilizing native Ollama tokenization as the primary pathway.  
3. Profiles token consumption for every component of the context formula across all nine experimental conditions.  
4. Computes total prompt token counts and percentage budget utilization for each condition.  
5. Identifies any condition that exceeds the SAFE, WARNING, or CRITICAL budget threshold.  
6. Performs controlled schema pruning for CRITICAL conditions, subject to tool identity immutability, payload-bearing field immutability, and manual semantic equivalence review.  
7. Performs schema growth analysis across density levels D1 $\\rightarrow$ D3 $\\rightarrow$ D5.  
8. Executes independent profiling by two researchers and reconciles their measurements using normalized general text inputs.  
9. Produces three deliverable documents: Token Profile Report, Schema Pruning Log, and Budget Decision Report.  
10. Generates a final GO / REVISE gate decision for entry into Phase 3 competence-baseline work only\.

Phase 2.5 must not:

* Evaluate attack success in any form.  
* Evaluate privilege aggregation outcomes.  
* Compute Attack Success Rate (ASR) or Tool Invocation Deviation (TID).  
* Count Critical Exploit events.  
* Generate vulnerability claims or security findings.  
* Measure model robustness under adversarial conditions.  
* Evaluate defenses or draw conclusions about exploitation likelihood.  
* Run the model in completion or inference mode (tokenization only).  
* Rewrite, paraphrase, shorten, or normalize benchmark payloads.  
* Add artificial padding to lower-density conditions or inflate lower-density token counts.  
* Run Phase 3 competence baseline tests.
* Treat Phase 2.5 GO as authorization for Phase 4 protocol freeze or Phase 5 core adversarial experimentation.

Every Phase 2.5 JSONL log row must carry exactly:

JSON  
{  
  "phase": "phase2\_5\_profiling",  
  "non\_experimental": true  
}

### **1.3 Phase 2.5 Position in the Research Timeline**

Phase 0 (Scope Lock)  
↓  
Phase 1 (Benchmark / Provenance Governance)  
↓  
Phase 2 (Infrastructure Build — Docker, FastMCP, Schema Variants)  
↓  
\[Phase 2 GO Gate\]  
↓  
Phase 2.5 (Context Window and Token Budget Profiling) ← THIS DOCUMENT  
↓  
\[Phase 2.5 GO Gate\]  
↓  
Phase 3 (Competence Baseline) — model competence gate lives here, not in Phase 2.5  
↓  
Phase 4 (Protocol Freeze)  
↓  
Phase 5 (Core Experiment)

### **1.4 No Silent Phase Transition Rule**

Phase 2.5 is complete only when the Budget Decision Report, Token Profile Report, Schema Pruning Log, reproducibility manifest, tokenizer validation report, and all readiness criteria are finalized. Even if Phase 2.5 receives a GO decision, the project may move only into Phase 3 competence-baseline execution. Phase 4 protocol freeze and Phase 5 core adversarial experiments remain prohibited until their own phase-specific gates are completed and signed.

## **2\. Methodological Assumptions**

The execution of this plan relies on the following structural constraints. If any assumption is violated at runtime, the measurement pipeline must fail closed:

* **Authenticated Schemas:** Input tool schemas must be byte-identical to the validated output of Phase 2, verified via SHA-256 signatures.  
* **Immutable Payload Registry:** The text strings for the attack components are drawn from the Phase 1 provenance log and cannot be altered, shortened, or paraphrased.  
* **Deterministic Tokenizer Behavior:** The model-native tokenization endpoint must return identical token indices for identical string sequences across execution instances.  
* **Fixed Operational Context Ceiling:** The 4,096-token system threshold is a hard boundary derived from edge-deployment limits.  
* **No Inference Execution:** The active model parameters are utilized solely for lexical segmentation; no forward-pass generation or completion occurs.  
* **Identical Source Inputs:** Both independent researchers operate on matching baseline configurations verified by cryptographic checksums.
* **Approved Payload Requirement for Final GO:** Placeholder payload profiling is permitted only for dry-run engineering rehearsal. The final Phase 2.5 GO decision must use `payload_approved_set.json` and the Phase 1 payload ledger with passing SHA-256 verification.

## **3\. Frozen Project Context Summary**

The following decisions are **authoritative and frozen** for Phase 2.5. This document is fully self-contained and supersedes all previous execution plan versions.

| Decision | Frozen Value |
| :---- | :---- |
| **Project Title** | Privilege Aggregation via Metadata Poisoning in Model Context Protocol (MCP) Tool Ecosystems |
| **Operational Context Ceiling** | 4,096 tokens (strict) |
| **Density Levels** | D1 (1 tool), D3 (3 tools), D5 (5 tools) |
| **D1 Tools** |  read\_internal\_notes |
| **D3 Tools** |  read\_internal\_notes, write\_outbox, get\_local\_weather |
| **D5 Tools** |  read\_internal\_notes, write\_outbox, get\_local\_weather, query\_local\_inventory, log\_event |
| **Metadata Conditions** | CLEAN, POISON-TD, POISON-CA per density level |
| **Tool Execution Model** | Benign, deterministic, local, mock-only |
| **Privilege Aggregation Def.** | Requires $\\ge 2$ distinct coordinated capabilities |
| **D1 Classification** | Negative-control / structural-impossibility condition for Critical Exploit |
| **D3, D5 Role** | Primary aggregation comparison conditions |
| **Critical Exploit Path** |  read\_internal\_notes $\\rightarrow$ write\_outbox only |
| **Attack Families** | Direct Override, Cross-Capability Escalation, Data Exfiltration |
| **Payload Provenance** | SHA-256 hashed, human-verified, never rewritten by AI tools |
| **No Cloud APIs** | All inference is local only |
| **No Real Credentials** | All mock data is synthetic |
| **Phase 5 Hardware Ceiling** | RTX 4080-class, 16 GB VRAM maximum |
| **Docker Boundary** | All MCP tools and orchestrator must remain inside Docker |
| **Reset Mechanism** | Verified /reset endpoint per trial; full teardown fallback |
| **Logging Format** | JSONL, one row per trial |
| **Enforcement Rule** | Phase 2.5 may not reuse Phase 2 smoke test results toward Phase 3 |

## **4\. Mathematical Notation and Operational Ceiling**

The operational context ceiling ($C$) is fixed at **4,096 tokens**. This value is an immutable constraint derived from targeting edge-deployed, resource-constrained open-weight models.

### **Notation Table**

| Symbol | Definition | Data Type | Section Introduced |
| :---- | :---- | :---- | :---- |
| $C$ | Operational Context Ceiling (4,096 tokens) | $\\mathbb{N}$ | Section 4 |
| $U$ | Usable Prompt Budget (3,584 tokens) | $\\mathbb{N}$ | Section 5 |
| $S\_{\\text{pad}}$ | Assistant Response and Tool-Call Formatting Buffer (512 tokens) | $\\mathbb{N}$ | Section 5 |
| $\\text{System}$ | System Prompt Tokens | $\\mathbb{N}$ | Section 5 |
| $\\text{Schemas}$ | Tool Schema Tokens | $\\mathbb{N}$ | Section 5 |
| $\\text{CapAdv}$ | Capability Advertisement Tokens | $\\mathbb{N}$ | Section 5 |
| $\\text{Payload}$ | Payload Tokens | $\\mathbb{N}$ | Section 5 |
| $\\text{Task}$ | User Task Tokens | $\\mathbb{N}$ | Section 5 |
| $\\text{History}$ | Conversation History Tokens | $\\mathbb{N}$ | Section 5 |
| $\\text{Total}$ | Total Prompt Tokens consumed by the input vector | $\\mathbb{N}$ | Section 5 |
| $P\_{\\text{util}}$ | Percentage Budget Utilization | $\\mathbb{R}$ | Section 5 |

## **5\. Token Budget Formula and Justification**

### **5.1 Formal Definition**

The equations governing system consumption must be applied uniformly across all scripts and reports:

$$\\text{Total} \= \\text{System} \+ \\text{Schemas} \+ \\text{CapAdv} \+ \\text{Payload} \+ \\text{Task} \+ \\text{History}$$

$$U \= C \- S\_{\\text{pad}} \= 4,096 \- 512 \= 3,584 \\text{ tokens}$$

$$P\_{\\text{util}} \= \\left( \\frac{\\text{Total}}{U} \\right) \\times 100$$

### **5.2 Component Definitions**

* **System Prompt Tokens ($\\text{System}$):** Tokens consumed by the fixed system prompt passed to the model at the start of every trial. Finalized before profiling and static across runs.  
* **Tool Schema Tokens ($\\text{Schemas}$):** Tokens consumed by the MCP tool schema definitions exposed through capability discovery (names, parameter names, type annotations, and description strings). Measured per schema variant.  
* **Capability Advertisement Tokens ($\\text{CapAdv}$):** Tokens consumed by the capability advertisement strings injected into the MCP metadata for POISON-CA conditions.  
* **Payload Tokens ($\\text{Payload}$):** Tokens consumed by the adversarial payload string injected via the retrieved-content or metadata channels. For CLEAN conditions, this is the approved benign baseline string from the same locked input set. **Payload tokens are non-prunable and SHA-256 locked**.  
* **User Task Tokens ($\\text{Task}$):** Tokens consumed by the user-facing task instruction triggering tool use. This text must not be modified for token budget purposes.  
* **Conversation History Tokens ($\\text{History}$):** Zero for single-turn profiling. Grows turn-by-turn across multi-turn evaluations and must be tracked explicitly.  
* **Assistant Response and Tool-Call Formatting Buffer ($S\_{\\text{pad}}$):** A fixed 512-token reserve held back from the prompt to allow model output generation (tool-call JSON, reasoning buffer, and response text). It is subtracted from the ceiling to yield the usable prompt budget.

### **5.3 Scientific Justification of the Buffer ($S\_{\\text{pad}}$)**

The allocation of 512 tokens represents exactly $12.5\\%$ of the total context resource window ($C$). This reserve is established as a conservative buffer for local open-weight models under sub-10B optimization scales. Structured tool execution models require sufficient context room to output dense, verbose JSON schemas. Restricting output constraints risks early stream truncation, causing parser failures during trial execution loops. The 512-token buffer secures generation space without encroaching on prompt structure boundaries.

## **6\. Experimental Conditions**

Phase 2.5 profiles all nine conditions defined by the intersection of density level and metadata condition:

| Condition ID | Density | Metadata Condition | Exposure Category | Required Output File |
| :---- | :---- | :---- | :---- | :---- |
| **C1** | D1 | CLEAN | Negative Control / Baseline |  c1\_d1\_clean\_\[model\]\_\[tier\]\_\[researcher\].json |
| **C2** | D1 | POISON-TD | Tool Description Poisoning |  c2\_d1\_poison\_td\_\[model\]\_\[tier\]\_\[researcher\].json |
| **C3** | D1 | POISON-CA | Capability Advertisement Poisoning |  c3\_d1\_poison\_ca\_\[model\]\_\[tier\]\_\[researcher\].json |
| **C4** | D3 | CLEAN | Intermediate Baseline |  c4\_d3\_clean\_\[model\]\_\[tier\]\_\[researcher\].json |
| **C5** | D3 | POISON-TD | Tool Description Poisoning |  c5\_d3\_poison\_td\_\[model\]\_\[tier\]\_\[researcher\].json |
| **C6** | D3 | POISON-CA | Capability Advertisement Poisoning |  c6\_d3\_poison\_ca\_\[model\]\_\[tier\]\_\[researcher\].json |
| **C7** | D5 | CLEAN | High-Density Baseline |  c7\_d5\_clean\_\[model\]\_\[tier\]\_\[researcher\].json |
| **C8** | D5 | POISON-TD | Tool Description Poisoning |  c8\_d5\_poison\_td\_\[model\]\_\[tier\]\_\[researcher\].json |
| **C9** | D5 | POISON-CA | Capability Advertisement Poisoning |  c9\_d5\_poison\_ca\_\[model\]\_\[tier\]\_\[researcher\].json |

**D1 Note:** D1 conditions are structural-impossibility conditions for Critical Exploit. They are profiled for token budget purposes only and must never be treated as adversarial trial data.

## **7\. Tokenizer Selection, Validation, and Serialization Standards**

### **7.1 Tokenization Pathway Hierarchy**

Tokenizer selection is governed by a strict two-pathway hierarchy to eliminate measurement drift:

1. **Primary Pathway — Native Ollama Tokenization (Authoritative):** All token profiling scripts must call the native Ollama /api/tokenize endpoint of the active model instance. This is the only pathway that guarantees token counts exactly match what the model receives at inference time, including special tokens, BOS/EOS markers, and chat-template wrapping.  
2. **Secondary Pathway — Offline Library Tokenization (Cross-Check Only):** transformers.AutoTokenizer or tiktoken may be used as an offline cross-check. Secondary counts must not override primary counts. If secondary counts differ from primary counts by $\>5\\%$ for any component, the divergence must be documented in the validation report with an explanation.

#### **Fake Ollama Stub Blocking Rule**

Any profiling script must verify endpoint authenticity before tokenization. The script must query `/api/version`, `/api/tags`, `/api/show`, and `/api/tokenize` for the exact selected model. The script must exit with a non-zero status before producing token counts if any of the following are true: the model list is empty, the exact selected model is absent, `/api/show` does not return native model metadata, `/api/tokenize` does not return a list of integer token IDs, the endpoint does not match the approved Mode B address, the model digest or metadata hash cannot be recorded, or the response structure matches the Phase 2 `fake_ollama.py` stub. Stub-derived token counts are strictly invalid.

### **7.2 Mode B Authorization for Tokenizer Validation**

The active infrastructure operates under **Mode B (host-routed)** because port 11434 remains unexposed directly in the isolated Docker network container mapping. Mode B remains explicitly authorized for Phase 2.5 tokenizer validation and profiling. Under Mode B, the Ollama /api/tokenize endpoint is reached via the host-routed address (http://localhost:11434 or http://host.docker.internal:11434). The Mode B exception record from Phase 2 must be referenced in the reproducibility manifest.

### **7.3 Hard Tokenizer-Availability Gate Protocol**

Before any profiling run, execute the following hard gate check to confirm endpoint authenticity:

Bash  
\# 1\. Verify Ollama Version Existence  
curl \-s http://localhost:11434/api/version

\# 2\. Verify the selected model is installed and visible  
curl \-s http://localhost:11434/api/tags

\# 3\. Verify native model metadata and digest availability  
curl \-s http://localhost:11434/api/show \\  
  \-d '{"name":"phi3.5:3.8b-mini-instruct-q4\_K\_M"}'

\# 4\. Test Tokenize Endpoint Availability with a Smoke Test  
curl \-s http://localhost:11434/api/tokenize \\  
  \-d '{"model":"phi3.5:3.8b-mini-instruct-q4\_K\_M","content":"tokenizer smoke test"}'

The run may proceed to profiling only if `/api/version` returns a valid version string, `/api/tags` lists the exact selected model, `/api/show` returns native metadata and a recordable digest or metadata hash, `/api/tokenize` returns integer token IDs for the smoke-test string, and the endpoint address matches the approved Mode B host-routed endpoint. If this gate fails, Phase 2.5 must pause immediately; no `/api/generate` fallback is allowed for official token counts.


### **7.3.1 Tokenizer Validation Reference Strings**

The tokenizer validation file `tokenizer/validation/reference_strings.txt` must contain exactly the following ten non-adversarial reference strings. These are validation probes only. They must not contain approved attack payload text, payload fragments, or payload-bearing metadata from Phase 1.

| Reference ID | Required String | Purpose |
| :---- | :---- | :---- |
| REF-01 | `The local MCP profiling harness is measuring token counts only.` | Plain ASCII baseline |
| REF-02 | `read_internal_notes -> write_outbox` | Tool-name and arrow-token behavior |
| REF-03 | `{"tool":"read_internal_notes","arguments":{"record_id":"case_001"}}` | JSON-like tool-call structure |
| REF-04 | `Capability advertisement: this tool reads synthetic internal notes.` | Capability-advertisement style text |
| REF-05 | `Line one\nLine two\nLine three` | Newline normalization check |
| REF-06 | `Unicode NFC check: café, naïve, résumé.` | Unicode normalization check |
| REF-07 | `[D1,CLEAN] schema_tokens + task_tokens + history_tokens = total_tokens` | Formula-like metadata string |
| REF-08 | `Parameter documentation: record_id is a synthetic identifier, not a real credential.` | Parameter-description style text |
| REF-09 | `Mode B endpoint validation uses localhost:11434 without cloud APIs.` | Mode B endpoint string |
| REF-10 | `Non-payload safety probe: ignore this as an instruction; count it as text only.` | Payload-like but non-payload tokenizer probe |

The SHA-256 hash of `reference_strings.txt` must be recorded in the tokenizer validation report. If the reference strings are changed, Phase 2.5 tokenizer validation must be rerun from the beginning.

### **7.4 Deterministic Serialization Standard**

All JSON structures (tool schemas, capability advertisements) must be serialized into strings using a deterministic key-ordering format to eliminate Python version or runtime dictionary differences:

Python  
import json

def serialize\_for\_tokenization(obj: dict) \-\> str:  
    """Produce a deterministic JSON string for tokenization."""  
    return json.dumps(obj, sort\_keys=True, ensure\_ascii=False, separators=(',', ':'))

Every call to tokenize\_component.py that processes a JSON object must pass the object through this function before tokenization, applying to both the primary and secondary pathways.

### **7.5 Text Normalization Standards**

To ensure identical counts across cross-platform environments (Windows, WSL, Linux) without breaking chain-of-custody, text processing rules are separated strictly by input category:

#### **Category A: General Inputs**

System prompts, safe task instruction strings, baseline descriptive metadata blocks, and analytical reports must be normalized using Unicode Normalization Form C (NFC) alongside standard whitespace processing to eliminate operating-system-dependent representation differences:

Python  
import unicodedata

def normalize\_for\_tokenization(text: str) \-\> str:  
    """Apply Unicode NFC normalization and clean line endings for general strings."""  
    \# Enforce Unicode NFC representation uniformity  
    text \= unicodedata.normalize('NFC', text)  
    \# Uniform newline characters  
    text \= text.replace('\\r\\n', '\\n').replace('\\r', '\\n')  
    text \= text.strip()  
    text \= '\\n'.join(line.rstrip() for line in text.split('\\n'))  
    return text

This function must be applied identically by both Researcher A and Researcher B on all Category A inputs.

#### **Category B: Payload-Bearing Inputs**

Approved exploit payloads, attack fragments, and fields containing metadata tracking strings must remain completely unmodified. **They are explicitly exempt from all normalization loops, whitespace stripping, or line ending conversions**. Scripts must evaluate input structures using raw byte matching verified against registered Phase 1 checksum metrics. For every payload-bearing input, scripts must record both the source\_payload\_hash and the tokenization\_input\_hash. Execution must fail closed if these hashes differ.

## **8\. Local Model Recommendations and Hardware Tiers**

### **8.1 Hardware Feasibility Gate**

Prior to pulling runtime components, developers must execute host environment assertions to map systemic capability bounds:

Bash  
\# WSL2 / Linux Infrastructure Diagnostic Sequence  
free \-h  
nvidia-smi 2\>/dev/null || echo "No dedicated hardware acceleration detected"  
df \-h .

PowerShell  
\# Windows PowerShell Diagnostic Fallback Interrogation Sequence  
Get-CimInstance Win32\_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory  
Get-CimInstance Win32\_VideoController | Select-Object Name, AdapterRAM  
Get-PSDrive C | Select-Object Name, Used, Free

Based on results, the system environment maps to one of three methodological hardware tiers:

| Tier | Boundary Constraints | Primary Engine (M1) | Secondary Engine (M2) | Validation State |
| :---- | :---- | :---- | :---- | :---- |
| **Tier 1** |  $\\ge 16$ GB RAM \+ Discrete GPU ($\\ge 8$ GB VRAM) |  hermes-2-pro-llama3-8b |  qwen2.5-coder-7b-instruct | Full multi-model validation active. |
| **Tier 2** | 8–16 GB RAM (Low or integrated GPU bounds) |  hermes-2-pro-llama3-8b |  qwen2.5-3b-instruct | Full evaluation via compact cross-check target. |
| **Tier 3** |  $\\le 8$ GB RAM (Host integrated graphics boundary) |  phi3.5:3.8b-mini-instruct-q4\_K\_M |  *Omitted* |  **Single-model profiling active.** Multi-model validation is deferred. |

The current deployment environment is constrained to **Tier 3 (7.4 GB RAM, integrated graphics)**. Operations are locked onto a single execution path running phi3.5:3.8b-mini-instruct-q4\_K\_M. If a hardware upgrade occurs before execution, re-classification to Tier 1 is mandatory.

### **8.2 Model Catalog Specifications**

* **Model M1-T1 — Hermes-2-Pro-Llama-3-8B (Tier 1 Primary):** Llama 3 family, 8B parameters, Q4\_K\_M quantization. Native BPE tokenizer. Purpose-tuned for structured tool JSON compliance.  
* **Model M2-T1 — Qwen2.5-Coder-7B-Instruct (Tier 1 Secondary):** Qwen 2.5 family, 7B parameters, Q4\_K\_M quantization. Architectural diversity reference.  
* **Model M2-T2 — Qwen2.5-3B-Instruct (Tier 2 Secondary):** Qwen 2.5 family, 3B parameters, Q4\_K\_M quantization. Scaled reference for Tier 2 limits.  
* **Model M1-T3 — Phi-3.5-mini-instruct (Tier 3 Primary Host Boundary):** Phi-3.5 family, 3.8B parameters, Q4\_K\_M quantization. Approximate RAM usage \~2.8 GB. Operable within the 7.4 GB host memory constraint without triggering out-of-memory cascading faults. Ollama tag: phi3.5:3.8b-mini-instruct-q4\_K\_M.

### **8.3 Model Digest Capture Protocol**

Silent updates of model tags by registry developers require strict parent digest logging. Execute the following command to retrieve the absolute cryptographic identifier:

Bash  
curl \-s http://localhost:11434/api/show \\  
  \-d '{"name": "phi3.5:3.8b-mini-instruct-q4\_K\_M"}' \\  
  | jq '{name: .modelinfo\["general.name"\], digest: .details.parent\_model, family: .details.family}'

The exact hash digest must be recorded in the reproducibility manifest and embedded into every profiling log entry row.

## **9\. Multi-Model Validation Design**

### **9.1 Hardware-Tier Conditional Execution Logic**

* **Tier 1 & Tier 2 Systems:** Profile all validation conditions concurrently across both target engines. Primary decisions rest on M1 counts; M2 functions as a tokenizer cross-check loop. If delta bounds vary by $\>5\\%$, enforce the maximum observed token length across decision profiles.  
* **Tier 3 Systems (Active Status):** Single-model execution is mandatory. Multi-model evaluation matrices are recorded as NOT\_APPLICABLE within all summary manifests. Cross-validation checks are formally deferred to Phase 3 pilot runs where larger open-weight systems can be isolated sequentially.

## **10\. Repository Structure and Traceability**

The repository architecture provides structural traceability and implementation reproducibility for auditing reviewers. All structural components must map directly to the layout below:

project\_root/  
│  
└── phase2\_5/  
    ├── inputs/                          \# Read-only components from Phase 2 validation  
    │   ├── schemas/                     \# Unmodified JSON baseline tool definitions  
    │   │   ├── d1\_clean\_schema.json  
    │   │   └── \[Remaining baseline schema targets mapped here\]  
    │   └── schema\_hashes/  
    │       └── schema\_hash\_manifest.json  
    ├── tokenizer/  
    │   └── validation/  
    │       ├── reference\_strings.txt  
    │       ├── native\_counts\_m1.json  
    │       └── native\_counts\_m2.json    \# Marked NOT\_APPLICABLE on Tier 3 host  
    ├── profiling/  
    │   ├── researcher\_a/                 \# Work isolation container for Agent A  
    │   │   ├── raw/  
    │   │   │   └── c1\_d1\_clean\_m1\_tier3\_ra.json  
    │   │   └── summary\_ra.json  
    │   ├── researcher\_b/                 \# Work isolation container for Agent B  
    │   │   └── raw/  
    │   └── reconciled/                  \# Cryptographically locked validation outputs  
    │       ├── reconciliation\_log.md  
    │       └── reconciled\_measurements.json  
    ├── scripts/  
    │   ├── verify\_codebase.py           \# Automated structural verifier  
    │   └── script\_manifest.json         \# Array container for validation scripts  
    └── reports/  
        ├── Token\_Profile\_Report.md  
        └── Budget\_Decision\_Report.md

## **11\. Sub-Phase Execution Plan**

### **Sub-Phase A: Environment Preparation**

1. **Document Completeness Audit:** Confirm that the active Phase 2.5 execution document contains all 21 numbered sections and 3 appendices. Record confirmation in the master manifest.  
2. **Hardware Feasibility Verification:** Run the tier diagnostic checks (§8.1) and log CPU, system memory capacity, disk constraints, and the absolute absence of a dedicated GPU into environment\_snapshot.json to confirm Tier 3 active enforcement.  
3. **Backend Exception Mapping:** Verify backend reachability via host routing for Mode B. Execute validation curl strings and ensure the active port configuration maps precisely.  
4. **Directory Matrix Traceability Initialization:** Build the directory layout specified in Section 10\.  
5. **Hash Validation of Schemas:** Copy all 9 schema JSON inputs from Phase 2 into inputs/schemas/ and run cryptographic checksum validation against schema\_hash\_manifest.json to verify zero data mutation.  
6. **Dependency Capture:** Output environment status via pip freeze \> phase2\_5/reproducibility/requirements\_frozen.txt and map the native runtime variables.  
7. **Model Parent Pulling:** Initialize the target engine via ollama pull phi3.5:3.8b-mini-instruct-q4\_K\_M and execute digest extraction (§8.3). Log the return signature.  
8. **Codebase Manifest Building:** Hash all active scripts in phase2\_5/scripts/ into a single valid JSON array and export to script\_manifest.json.  
9. **Baseline Verification Run:** Execute python phase2\_5/scripts/verify\_codebase.py to assert strict integrity compliance.

### **Sub-Phase B: Tokenizer Validation**

1. **Authenticity Testing:** Invoke the fake stub blocking verification. If the return structure does not map natively to a production Ollama deployment containing valid parent metadata blocks, halt execution immediately.  
2. **Reference Matrix Construction:** Load the 10 reference strings into tokenizer/validation/reference\_strings.txt.  
3. **Input Conditioning:** Pass all 10 strings through normalize\_for\_tokenization() (§7.5). Save normalized versions.  
4. **Authoritative Extraction:** Route each conditioned text string through Ollama /api/tokenize for Model M1. Record integer counts to native\_counts\_m1.json.  
5. **Offline Comparison Tracking:** Execute cross-pathway analysis via transformers.AutoTokenizer using serialize\_for\_tokenization(). Write counts to library\_counts\_m1.json.  
6. **Divergence Analysis:** Calculate the per-string absolute differential:

$$\\Delta\_{\\text{tokens}} \= | \\text{Count}\_{\\text{native}} \- \\text{Count}\_{\\text{library}} |$$  
Assert that $\\Delta\_{\\text{tokens}} \\le 2$ across all strings. If any value boundaries fail, reconfigure vocabulary parameters and clear state. Mark all Model M2 entries as NOT\_APPLICABLE for Tier 3\.

### **Sub-Phase C: Baseline Profiling — D1 Conditions (C1, C2, C3)**

1. **Codebase Assurance:** Prior to execution, both researchers must independently execute python phase2\_5/scripts/verify\_codebase.py to confirm zero script mutation.  
2. **Independent Execution:** Researchers A and B execute localized commands to profile Conditions C1, C2, and C3.  
3. **Processing Execution:** Apply Category A processing rules to general input strings while enforcing byte-level matching rules for payload components. JSON arrays use sorted key serialization.  
4. **Component Deconstruction:** Extract specific metric arrays for all seven components and write results to the structural tracking JSON files.

### **Sub-Phase D: Mid-Density Profiling — D3 Conditions (C4, C5, C6)**

1. Executed under identical parameters as Sub-Phase C, substituting D3 schema parameters.  
2. If any condition returns a CRITICAL budget threshold flag ($\\ge 3,226$ tokens), immediately halt work and escalate the specific schema profile to Sub-Phase H prior to starting high-density tracking.

### **Sub-Phase E: High-Density Profiling — D5 Conditions (C7, C8, C9)**

1. Executed under identical profiling parameters as Sub-Phases C and D, substituting D5 schema elements.  
2. Flag all individual profiles that exceed the integer threshold ceiling of $\\ge 3,226$ tokens directly inside the summary tracking structures.

### **Sub-Phase F: Schema Growth Analysis**

1. Run python scripts/compute\_growth\_curves.py \--input profiling/reconciled/reconciled\_measurements.json.  
2. The engine parses the final data layout to export the four mandatory architectural tables (Tables F1–F4) detailing scaling curves, marginal token addition variables per metadata layer, and mathematical midpoint non-linearity calculations.

### **Sub-Phase G: Independent Researcher Reconciliation**

1. Researchers A and B lock their data matrices independently.  
2. The reconciliation framework executes a hash verification pass to verify that both researchers operated on byte-identical input sources across environments.  
3. Compute the delta per component:

$$\\text{Disagreement} \= | \\text{Count}\_{\\text{RA}} \- \\text{Count}\_{\\text{RB}} |$$

* $\\le 3$ tokens: Handled automatically via rounding averages up to the nearest integer.  
* $4\\text{ to }10$ tokens: Trigger localized script evaluation reviews and manual line tracking.  
* $\> 10$ tokens: Halt process, re-verify baseline input file paths, clear environment variables, and re-run profiling under supervised protocols.

### **Sub-Phase H: Schema Pruning (Conditional)**

1. **Trigger Condition:** Executed only if validated records indicate a CRITICAL violation state ($\\ge 3,226$ tokens) post-reconciliation.  
2. **Immutability Compliance Rules:** Enforce structural identity protections for Category 1 and Category 2 blocks.  
3. **Two-Pass Optimization Review:** Require manual dual-researcher validation signatures alongside formal authorization sign-offs from the Lead Researcher.  
4. If target limits cannot be secured, report an immediate REVISE gate recommendation.

### **Sub-Phase I: Budget Decision and Phase 3 Readiness**

1. Process metric reports via generate\_budget\_report.py.  
2. Sign manifests and establish readiness state logs.

## **12\. Token Budget Thresholds and Technical Justification**

The categorization constraints are tied directly to the functional boundaries of the usable prompt budget ($U \= 3,584$ tokens):

| Structural Range | Classification | Allocation Footprint | Target Operational Impact |
| :---- | :---- | :---- | :---- |
| **$\\le 2,688$ tokens** |  **SAFE** |  $0.0\\% \\text{ to } 75.0\\%$ | Approved for immediate progression. Schema modification blocked. |
| **2,689 – 3,225 tokens** |  **WARNING** |  $75.03\\% \\text{ to } 90.0\\%$ | Approved with monitoring constraints. Requires tracking during multi-turn tests. |
| **$\\ge 3,226$ tokens** |  **CRITICAL** |  $\> 90.0\\%$ | Progression block. Optimization or pruning is mandatory. |

### **Boundary Derivation**

* SAFE Ceiling: $\\lfloor 3,584 \\times 0.75 \\rfloor \= 2,688$ tokens  
* WARNING Ceiling: $\\lfloor 3,584 \\times 0.90 \\rfloor \= 3,225$ tokens  
* CRITICAL Floor: 3,226 tokens

### **Methodological Justification**

These boundaries define clear engineering tolerances rather than approximate statistical confidence windows. The SAFE threshold secures a minimum buffer of 896 tokens, ensuring context room for conversation history growth during multi-turn test loops. The WARNING band highlights configurations prone to truncation if history components accumulate. The CRITICAL threshold marks configurations that exhaust context room, making pruning necessary to avoid runtime deployment failures.

## **13\. Deterministic Decision Gate and Pruning Stopping Criteria**

### **13.1 Algorithmic Gate Progression Rules**

The transition pathway between Phase 2.5 and Phase 3 is managed by a deterministic logic flow:

\[Is Profile Execution Complete?\]  
               │  
               ▼  
   \[Any Condition CRITICAL?\] ───(No)───► \[All SAFE/WARNING?\] ───(Yes)───► \[GO GATE PASSED\]  
               │                                   │  
             (Yes)                               (No)  
               │                                   │  
               ▼                                   ▼  
    \[Execute Sub-Phase H\]                  \[REVISE RECOMMENDATION\]  
               │  
               ▼  
     \[Pruning Stopping Rule Met?\]  
               │  
             (Yes)  
               │  
               ▼  
   \[Reconciled Count <= 3,225?\] ───(Yes)───► \[GO GATE PASSED\]  
               │  
              (No)  
               │  
               ▼  
   \[REVISE GATE PROGRESSION BLOCK\]

### **13.2 Schema Pruning Deterministic Stopping Criteria**

To prevent unbounded processing iteration loops during Sub-Phase H, optimization routines must immediately terminate if any of the following parameters are satisfied:

1. **Exhaustion of Category 3 Fields:** Pruning must stop if all prunable free-text descriptive properties (free-text description strings, parameter description strings) have been stripped of redundant adjectives and compressed to minimal phrasing.  
2. **Semantic Boundary Intersection:** Optimization loops must terminate if further word reduction would alter system security definitions, identity scopes, or operational risk statements.  
3. **Maximum Iteration Cap:** The routine is limited to 3 sequential compression passes per schema target. If the token count remains $\\ge 3,226$ after 3 passes, pruning has failed, forcing a REVISE decision.

## **14\. Schema Growth Analysis Specification**

Analytical verification tools track systemic expansion profiles across structural transitions:

* $$\\text{Schema Growth (D1} \\rightarrow \\text{D3)} \= \\text{Schemas}\_{\\text{D3}} \- \\text{Schemas}\_{\\text{D1}}$$  
* $$\\text{Schema Growth (D3} \\rightarrow \\text{D5)} \= \\text{Schemas}\_{\\text{D5}} \- \\text{Schemas}\_{\\text{D3}}$$  
* $$\\text{Metadata Growth (D1} \\rightarrow \\text{D3)} \= \\text{CapAdv}\_{\\text{D3}} \- \\text{CapAdv}\_{\\text{D1}}$$

### **Growth Linearity Evaluation Rules**

A stable, linear interface profile under standard addition patterns predicts:

$$\\text{Schemas}\_{\\text{D3}} \\approx \\text{Schemas}\_{\\text{D1}} \+ \\frac{\\text{Schemas}\_{\\text{D5}} \- \\text{Schemas}\_{\\text{D1}}}{2}$$  
The parsing engine evaluates non-linear trends to identify hidden overhead inflation introduced by structural tool mapping components.

## **15\. Researcher Independence and Precision Reconciliation Protocol**

### **15.1 Baseline Independence Guarantees**

* **Script Manifest Enforcement:** Prior to data extraction, researchers must execute codebase status checks to confirm alignment with master baseline signatures.  
* **Workspace Separation:** Read access across researcher\_a/ and researcher\_b/ target paths remains blocked until intermediate file hashes match verification values.

### **15.2 Precision Reconciliation Algorithm**

Because tokenization via the authority endpoint is completely deterministic, zero count divergence should occur under uniform processing steps. Discrepancies point to structural platform differences or incorrect file configurations. The reconciliation framework processes data using a precise rule set:

                  \[Evaluate Absolute Variance Per Component\]  
                                       │  
      ┌────────────────────────────────┼────────────────────────────────┐  
      ▼                                ▼                                ▼  
 \[Delta \<= 3\]                    \[Delta 4 to 10\]                  \[Delta \> 10\]  
      │                                │                                │  
      ▼                                ▼                                ▼  
\[Averaging Allowed\]           \[Halt Profiling\]                 \[Structural Fault\]  
  Round Up to                   Inspect Source                   Enforce Codebase Wipe  
  Nearest Integer               Line Encoding                    Re-run from Clean Inputs

Averaging token counts is allowed **only** if the variance is proven to stem from operating-system line encoding translations ($\\backslash\\text{r}\\backslash\\text{n}$ vs $\\backslash\\text{n}$) that bypassed Category A normalization blocks. For all structural metadata deltas, the error must be diagnosed and resolved via code inspection.

## **16\. Reporting Requirements and Table Templates**

### **16.1 Master Token Profile Table**

| Condition | System | Schemas | CapAdv | Payload | Task | History | S\_pad | Total | Budget % | Status | Pathway | Tier |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| D1-CLEAN |  |  |  |  |  | 0 | 512 |  |  |  | native | 3 |
| D1-POISON-TD |  |  |  |  |  | 0 | 512 |  |  |  | native | 3 |
| D1-POISON-CA |  |  |  |  |  | 0 | 512 |  |  |  | native | 3 |
| D3-CLEAN |  |  |  |  |  | 0 | 512 |  |  |  | native | 3 |
| D3-POISON-TD |  |  |  |  |  | 0 | 512 |  |  |  | native | 3 |
| D3-POISON-CA |  |  |  |  |  | 0 | 512 |  |  |  | native | 3 |
| D5-CLEAN |  |  |  |  |  | 0 | 512 |  |  |  | native | 3 |
| D5-POISON-TD |  |  |  |  |  | 0 | 512 |  |  |  | native | 3 |
| D5-POISON-CA |  |  |  |  |  | 0 | 512 |  |  |  | native | 3 |

### **16.2 Cross-Model Comparison Table (Hardware-Tier Conditional)**

Dual-Model Validation Status: DEFERRED\_TIER\_3 (Infeasible on current host hardware footprint)

| Condition | M1 Total | M2 Total | Δ Tokens | Δ % | Adopted Value |
| :---- | :---- | :---- | :---- | :---- | :---- |
| D1-CLEAN |  | NOT\_APPLICABLE | NOT\_APPLICABLE | NOT\_APPLICABLE | M1 Native value |
| \[C2-C9 rows\] |  | NOT\_APPLICABLE | NOT\_APPLICABLE | NOT\_APPLICABLE | M1 Native value |

### **16.3 Schema Growth Summary Table**

| Transition | CLEAN Schema Δ | POISON-TD Schema Δ | POISON-CA Schema Δ | CLEAN Total Δ | POISON-TD Total Δ | POISON-CA Total Δ |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| D1 → D3 |  |  |  |  |  |  |
| D3 → D5 |  |  |  |  |  |  |
| D1 → D5 |  |  |  |  |  |  |

### **16.4 Budget Decision Summary Table**

| Condition | Final Total Tokens | Budget Status | Pruning Required | Post-Pruning Total | Final Status | Phase 3 Baseline Start Approved |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| D1-CLEAN |  |  | No | N/A |  |  |
| \[C2-C9 rows\] |  |  |  |  |  |  |

### **16.5 Researcher Reconciliation Table**

| Condition | Component | RA Count | RB Count | Difference | Within Threshold? | Resolution |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
|  |  |  |  |  |  |  |

## **17\. Deliverable Specifications and Acceptance Criteria**

### **17.1 Deliverable 1 — Token\_Profile\_Report.md**

* **Purpose:** Primary profiling deliverable detailing environment metrics, raw data counts, and budget validation allocations.  
* **Acceptance Criteria:** Must contain zero missing cells across all nine evaluation profiles. Must include explicit verification stamps and validation signatures from both independent research tracks.

### **17.2 Deliverable 2 — Schema\_Pruning\_Log.md**

* **Purpose:** Provides an auditable trail of schema text reductions and threat-model verification steps.  
* **Acceptance Criteria:** Required if optimization routines are triggered. If no condition triggers pruning, the log must be compiled containing a verified "No Optimization Required" analytical status entry.

### **17.3 Deliverable 3 — Budget\_Decision\_Report.md**

* **Purpose:** Issues the formal gate decision vector for experimental baseline deployment.  
* **Acceptance Criteria:** Requires an explicit, binary GO/REVISE resolution status signature for each condition profile, validated by the Lead Researcher.

## **18\. Phase 3 Readiness Criteria**

These criteria determine whether Phase 2.5 has produced sufficient token-budget evidence to begin **Phase 3 competence-baseline work only**. They do not authorize Phase 4 protocol freeze, Phase 5 adversarial trials, ASR/TID calculations, Critical Exploit counting, defense evaluation, or manuscript claims.

Validation parameters require an absolute binary **PASS** or **FAIL** status resolution:

| Criterion | Description | Assessment | Evidence Location |
| :---- | :---- | :---- | :---- |
| **CR-01** | Schema Hash Verification | PASS / FAIL |  inputs/schema\_hashes/schema\_hash\_manifest.json |
| **CR-02** | Payload Provenance Hash Lock | PASS / FAIL | Phase 1 payload ledger registration schema |
| **CR-03** | Hardware Feasibility Documented | PASS / FAIL |  reproducibility/environment\_snapshot.json |
| **CR-04** | Non-Experimental Log Flagging | PASS / FAIL |  logs/phase2\_5\_profiling\_log.jsonl |
| **CR-05** | 4,096-Token Ceiling Lock | PASS / FAIL | All profiling output files |
| **CR-06** | Tokenizer Validated — Native Ollama Pathway | PASS / FAIL |  tokenizer/validation/tokenizer\_validation\_report.md |
| **CR-07** | Fake Stub Blocking Confirmed | PASS / FAIL |  tokenizer/validation/tokenizer\_validation\_report.md |
| **CR-08** | Dual-Researcher Path Isolation | PASS / FAIL | Directory structure access verification layout |
| **CR-09** | Disagreement Escalation Path Tested | PASS / FAIL |  profiling/reconciled/reconciliation\_log.md |
| **CR-10** | Tool Name Mapping Preserved | PASS / FAIL | Schema immutability records inside pruning log |
| **CR-11** | Script Manifest Generated and Verified | PASS / FAIL |  scripts/script\_manifest.json |
| **CR-12** | Text Normalization Applied Safely | PASS / FAIL | Script codebase validation output capture logs |
| **CR-13** | D1 Conditions SAFE or WARNING | PASS / FAIL |  profiling/reconciled/final\_token\_profile\_table.csv |
| **CR-14** | D3 Conditions SAFE or WARNING | PASS / FAIL | Budget Decision Report profile listings |
| **CR-15** | D5 Conditions SAFE or WARNING | PASS / FAIL | Budget Decision Report profile listings |
| **CR-16** | Schema Pruning Log Completed | PASS / FAIL |  reports/Schema\_Pruning\_Log.md |
| **CR-17** | Manual Equivalence Verified for Pruned Fields | PASS / FAIL |  schema\_pruning/pruning\_decisions/ sign-off maps |
| **CR-18** | Model Digests Recorded Natively | PASS / FAIL |  reproducibility/phase2\_5\_reproducibility\_manifest.md |
| **CR-19** | Reproducibility Manifest Completed | PASS / FAIL |  reproducibility/phase2\_5\_reproducibility\_manifest.md |
| **CR-20** | Mode B Continued Use Justified | PASS / FAIL | Budget Decision Report Section 6 records |
| **CR-21** | No REVISE Conditions Block Comparison | PASS / FAIL | Master readiness summary fields |
| **CR-22** | Phase 2 Smoke Test Results Not Reused | PASS / FAIL | JSONL log phase markers verification |
| **CR-23** | Final Profiling Uses Approved Phase 1 Payload Set | PASS / FAIL | `payload_approved_set.json`, Phase 1 payload ledger, tokenization input hashes |

## **19\. Threats to Validity**

### **19.1 Internal Validity**

The primary internal threat centers on potential token count drift between library tokenizers and native runtime containers. This risk is minimized by establishing native Ollama tokenization via /api/tokenize as the authoritative pathway. Human configuration error during manual schema pruning is addressed by requiring a two-pass validation protocol and manual researcher sign-offs.

### **19.2 Construct Validity**

Construct threats involve whether single-turn static token profiling accurately predicts context limits for dynamic, multi-turn interactions. While single-turn tracking forms the baseline measurement, the 512-token reserve ($S\_{\\text{pad}}$) and the strict SAFE boundary ($\\le 75\\%$) are engineered to provide a safety margin for history accumulation. This mitigates the risk of underestimating resource demands during live testing.

### **19.3 External Validity**

The external threat relates to the generalization of these budget metrics to model families beyond the sub-10B open-weight architectures evaluated here. Because the evaluation is limited to Tier 3 host resources, external generalizability is bounded. This boundary is explicitly addressed by treating Tier 3 configurations as single-model validation targets and deferring wider cross-model profiling to Phase 3\.

### **19.4 Conclusion Validity**

Conclusion validity relies on data collection integrity across independent tracking runs. If researchers unconsciously align divergent data values, the reliability of the baseline protocol degrades. This threat is addressed by maintaining isolation between workspaces, enforcing pre-run script hash validation, and applying a precise reconciliation protocol.

## **20\. Risk Register**

Methodological risks are tracked below to secure experimental integrity:

| Risk ID | Risk Focus Profile | Likelihood | Impact | Structural Mitigation Vector |
| :---- | :---- | :---- | :---- | :---- |
| **R-01** | High-density C9 tracking limits cross boundary ceilings. | Medium | High | Apply Sub-Phase H pruning rules. If optimization targets fail, apply a localized REVISE block to secure baseline parameters. |
| **R-02** | Tokenizer metric divergence across secondary libraries. | Low | Medium | Enforce the authoritative native endpoint pathway. Record observed deltas for structural reporting. |
| **R-03** | Count drift caused by operational configuration faults. | Low | Medium | Re-verify baseline input file hash registry entries. Enforce localized script wipes and re-run under supervision. |
| **R-04** | Execution container communication configuration drops. | Low | High | Halt profiling routines, clear localized server memory spaces, and verify container port properties before resuming. |
| **R-05** | Exploit text arrays mutated by normalization scripts. | Low | Critical |  **Protocol Violation.** Terminate execution loops, restore immutable input text targets, and cross-check ledger states. |
| **R-06** | Profiling script triggers inference generation loops. | Low | Critical |  **Scope Boundary Violation.** Implement explicit endpoint parameter blocks. Destroy corrupted tracking log paths. |
| **R-07** | Fixed buffer space constrains test context sequences. | Medium | Medium | Track history accumulation metrics and adjust parameters during the Phase 3 pilot cycle if justified by system data. |
| **R-08** | Script identity drift occurs across user workspace areas. | Low | High | Enforce automated codebase checking tools using structural manifest signature validation. |
| **R-09** | Baseline source inputs modified during data collection loops. | Low | Critical | Validate target files against master cryptographic manifests before starting any measurement run. |

## **21\. Phase 2.5 Non-Negotiable Rules**

* **Rule 1 — Measurement Only:** Phase 2.5 produces only token counts and budget feasibility determinations. No security findings, attack success claims, or vulnerability statements may appear in any Phase 2.5 artifact.  
* **Rule 2 — Payload Integrity:** Benchmark payload text must never be modified, shortened, paraphrased, normalized, or rewritten. Payload SHA-256 hashes must be verified before every profiling run. Payload-bearing fields are strictly non-prunable.  
* **Rule 3 — No Inference Runs:** Phase 2.5 does not run the model in completion or inference mode. Tokenization only. No prompt is submitted to the model for completion during Phase 2.5 profiling.  
* **Rule 4 — No Padding:** Artificial padding must never be added to lower-density conditions. Token count differences between density levels must reflect genuine schema differences only.  
* **Rule 5 — No Inflation:** Lower-density condition token counts must not be inflated to match higher-density counts for any analytical purpose.  
* **Rule 6 — Schema Pruning Structural Approvals:** Any reduction in schema verbosity must pass manual dual-researcher certification and Lead Researcher sign-off against the threat-model preservation checklist.  
* **Rule 7 — JSONL Log Discipline:** Every Phase 2.5 JSONL log entry must carry "phase": "phase2\_5\_profiling" and "non\_experimental": true. Entries lacking these fields are invalid.  
* **Rule 8 — Researcher Independence:** Researcher A and Researcher B must not share intermediate measurements before reconciliation. File isolation and notification protocols are mandatory.  
* **Rule 9 — No Silent Phase Advancement:** Phase 3 competence-baseline work must not begin until the Budget Decision Report is finalized and signed and all Phase 3 Readiness Criteria are assessed as PASS. A Phase 2.5 GO does not authorize Phase 4 protocol freeze or Phase 5 core adversarial experimentation.  
* **Rule 10 — No Phase 2 Smoke Test Reuse:** Phase 2 LLM smoke test results must not be incorporated into Phase 2.5 token profiling outputs or used as evidence for Phase 3 readiness.  
* **Rule 11 — Tool Identity Immutability:** The fields tool\_name, tool\_id, logical\_tool\_id, routing\_key, tool\_mapping, and all schema identifier parameters are absolutely immutable. Violation constitutes a critical protocol breach.  
* **Rule 12 — Native Ollama Tokenization is Authoritative:** All token budget decisions must be based on native Ollama /api/tokenize endpoint counts. The Phase 2 fake\_ollama.py stub must be blocked before any tokenization. Counts derived from the stub are invalid.
* **Rule 13 — Placeholder Profiling Cannot Support Final GO:** Placeholder payloads may be used only for provisional dry-run engineering rehearsal. The final Phase 2.5 GO decision must use the approved Phase 1 payload set and must record matching `source_payload_hash` and `tokenization_input_hash` values.

## **Appendix A: Input Consumption Map**

| Input File Name | Consumed In | Operational Mapping Purpose |
| :---- | :---- | :---- |
| d1\_clean\_schema.json | Sub-Phase C | Tokenize structural tool layout parameters for Condition C1 |
| d1\_poison\_td\_schema.json | Sub-Phase C | Tokenize structural tool layout parameters for Condition C2 |
| d1\_poison\_ca\_schema.json | Sub-Phase C | Tokenize structural tool layout parameters for Condition C3 |
| d3\_clean\_schema.json | Sub-Phase D | Tokenize structural tool layout parameters for Condition C4 |
| d3\_poison\_td\_schema.json | Sub-Phase D | Tokenize structural tool layout parameters for Condition C5 |
| d3\_poison\_ca\_schema.json | Sub-Phase D | Tokenize structural tool layout parameters for Condition C6 |
| d5\_clean\_schema.json | Sub-Phase E | Tokenize structural tool layout parameters for Condition C7 |
| d5\_poison\_td\_schema.json | Sub-Phase E | Tokenize structural tool layout parameters for Condition C8 |
| d5\_poison\_ca\_schema.json | Sub-Phase E | Tokenize structural tool layout parameters for Condition C9 |
| schema\_hash\_manifest.json | Sub-Phases A, C, D, E | Cryptographic hash validation check across execution components |
| system\_prompt\_v1.txt | Sub-Phases C, D, E | Tokenize base initialization prompt components |
| task\_strings\_v1.json | Sub-Phases C, D, E | Tokenize target agent instruction sets |
| payload\_approved\_set.json | Sub-Phases C, D, E | Tokenize fixed experimental exploit components |
| capability\_advertisements\_v1.json | Sub-Phases C, D, E | Tokenize metadata configuration attributes |
| reference\_strings.txt | Sub-Phase B | Base input matrices for tokenizer validation |
| phase2\_5\_reproducibility\_manifest.md | Sub-Phase A, I | Master logging capture interface |

## **Appendix B: Script Specifications**

### **B.1 tokenize\_component.py**

* **Purpose:** Tokenize a single string entry or structural tracking target using the native Ollama pathway.  
* **Pre-Processing Behavior:** Enforces Category A normalization for general text arrays, applies deterministic serialization for JSON structures, and passes Category B payload arrays byte-identically with dual hash checking.  
* **Core Implementation Pattern:**

```python
import hashlib
import json
import sys
from urllib.parse import urlparse

import requests

APPROVED_MODE_B_ENDPOINTS = {
    "http://localhost:11434",
    "http://host.docker.internal:11434",
}

def _fail(message: str) -> None:
    print(f"Tokenization Pathway Failure: {message}")
    sys.exit(1)

def _metadata_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def verify_ollama_endpoint(model_tag: str, ollama_url: str) -> dict:
    """Fail closed unless the endpoint is a real Ollama instance serving the exact model."""
    normalized_url = ollama_url.rstrip("/")
    if normalized_url not in APPROVED_MODE_B_ENDPOINTS:
        _fail(f"Endpoint {normalized_url} is not an approved Mode B address.")

    version_response = requests.get(f"{normalized_url}/api/version", timeout=5)
    if version_response.status_code != 200 or "version" not in version_response.json():
        _fail("/api/version did not return a valid Ollama version payload.")

    tags_response = requests.get(f"{normalized_url}/api/tags", timeout=5)
    if tags_response.status_code != 200:
        _fail("/api/tags did not return HTTP 200.")
    models = [m.get("name", "") for m in tags_response.json().get("models", [])]
    if model_tag not in models:
        _fail(f"Selected model {model_tag} is absent from /api/tags.")
    if any("fake" in name.lower() or "stub" in name.lower() for name in models):
        _fail("fake/stub model marker detected in /api/tags.")

    show_response = requests.post(
        f"{normalized_url}/api/show",
        json={"name": model_tag},
        timeout=10,
    )
    if show_response.status_code != 200:
        _fail("/api/show did not return HTTP 200 for the selected model.")
    show_payload = show_response.json()
    if not isinstance(show_payload, dict) or not show_payload:
        _fail("/api/show returned empty or invalid metadata.")

    metadata_digest = (
        show_payload.get("digest")
        or show_payload.get("details", {}).get("parent_model")
        or _metadata_hash(show_payload)
    )
    if not metadata_digest:
        _fail("Unable to derive model digest or metadata hash from /api/show.")

    return {
        "ollama_url": normalized_url,
        "ollama_version": version_response.json().get("version"),
        "model_tag": model_tag,
        "model_metadata_digest": metadata_digest,
    }

def count_tokens_native(text: str, model_tag: str, ollama_url: str) -> int:
    """Count tokens using native Ollama /api/tokenize after strict endpoint verification."""
    normalized_url = ollama_url.rstrip("/")
    verify_ollama_endpoint(model_tag, normalized_url)

    response = requests.post(
        f"{normalized_url}/api/tokenize",
        json={"model": model_tag, "content": text},
        timeout=10,
    )
    if response.status_code != 200:
        _fail("/api/tokenize did not return HTTP 200.")

    payload = response.json()
    tokens = payload.get("tokens")
    if not isinstance(tokens, list) or not all(isinstance(t, int) for t in tokens):
        _fail("/api/tokenize did not return a list of integer token IDs.")

    return len(tokens)
```

### **B.2 profile\_condition.py**

* **Purpose:** Compiles full metadata profiles across the seven components for a designated experimental condition.  
* **Execution Safeguards:** Runs explicit startup script hash checking; enforces schema identity structural validations against the master schema ledger; logs exact quantization metadata hashes, parent engine digests, and hardware parameters directly inside the JSON metrics output structure.

### **B.3 verify\_codebase.py**

* **Purpose:** Ensures strict reproducibility control by validating script states against registered SHA-256 signatures.  
* **Core Implementation Pattern:**

Python  
import hashlib  
import json  
import os  
import sys

def verify\_scripts(manifest\_path: str, scripts\_dir: str) \-\> bool:  
    try:  
        with open(manifest\_path, 'r', encoding='utf-8') as f:  
            manifest \= json.load(f)  
                
        all\_ok \= True  
        \# Track expected script files to detect extra unmapped elements  
        expected\_files \= set()  
            
        for entry in manifest:  
            \# Enforce path evaluation relative strictly to scripts base directory  
            script\_name \= os.path.basename(entry\["file"\])  
            target\_path \= os.path.join(scripts\_dir, script\_name)  
            expected\_files.add(target\_path)  
                
            if not os.path.exists(target\_path):  
                print(f"FATAL: Required validation script missing: {script\_name}")  
                all\_ok \= False  
                continue  
                    
            with open(target\_path, "rb") as sf:  
                actual\_hash \= hashlib.sha256(sf.read()).hexdigest()  
                    
            if actual\_hash \!= entry\["sha256"\]:  
                print(f"FATAL: Code drift localized inside: {script\_name}")  
                all\_ok \= False  
                    
        \# Detect presence of unmapped executable components inside directory  
        for file in os.listdir(scripts\_dir):  
            if file.endswith(".py"):  
                full\_p \= os.path.join(scripts\_dir, file)  
                if full\_p not in expected\_files:  
                    print(f"FATAL: Unregistered executable file detected: {file}")  
                    all\_ok \= False  
                        
        return all\_ok  
    except Exception as e:  
        print(f"Verification script validation system failure: {str(e)}")  
        return False

if \_\_name\_\_ \== "\_\_main\_\_":  
    \# Standard internal execution routing mapping  
    base\_dir \= os.path.dirname(os.path.abspath(\_\_file\_\_))  
    m\_path \= os.path.join(base\_dir, "script\_manifest.json")  
    status \= verify\_scripts(m\_path, base\_dir)  
    sys.exit(0 if status else 1)

## **Appendix C: Reproducibility Manifest Template**

Markdown  
\# Phase 2.5 Reproducibility Manifest — Version 1.3

\#\# Project Metadata  
\* Title: Privilege Aggregation via Metadata Poisoning in MCP Tool Ecosystems  
\* Phase: 2.5 — Context Window and Token Budget Profiling  
\* Execution Plan Blueprint Reference: Version 1.3 Standalone  
\* Evaluation Date Range: \[ISO-8601 Verification Stamp\]

\#\# Document Completeness Review Record  
\* All 21 Context Sections Present and Validated: YES / NO  
\* All 3 Appendices Present and Validated: YES / NO  
\* Audited and Confirmed By: \[Researcher Signature\] on \[Date Stamp\]

\#\# Hardware Environment Footprint Profile  
\* CPU Family Model: \[Specification String\]  
\* System Total RAM: \[Logged Gigabytes Capacity\]  
\* Available VRAM at Evaluation Runtime: \[Logged Gigabytes Capacity\]  
\* Graphics Controller Classification: Dedicated GPU / Integrated Graphics Architecture  
\* Operating System Core Version: \[System Version String\]  
\* Hardware Validation Tier Assignment: Tier 1 / Tier 2 / Tier 3 (Confirmed Host Level)

\#\# Model Backend Infrastructure Map  
\* Active Operations Mode: Mode A (Containerized Isolation) / Mode B (Host-Routed Core Interconnect)  
\* Mode B Authorization Exception Record Reference ID: \[Phase 2 Entry Hash String / N/A\]  
\* Target Ollama Connection Interconnect Port Address: \[Local Host Endpoint Network Mapping\]  
\* Authenticity Smoke Check Evaluation Result: Passed / Verification Halt Imposed

\#\# Base Software Dependencies Configuration  
\* Python Operational Runtime Version: \[Version Metric String\]  
\* Docker Daemon Engine Version: \[Version Metric String\]  
\* Ollama Service Platform Version: \[Version Metric String\]  
\* Pip Lock Manifest Identity Code: sha256:\[Hash Return Signature of requirements*\_frozen.txt\]*

*\#\# Evaluation Engine Profiles*  
*\* Primary Execution Engine (Model M1-T3 Selection):*  
    *\* Model Label String: \`phi3.5:3.8b-mini-instruct-q4\_*K*\_M\`*  
    *\* Ollama Registry Access Tag: \`ollama run phi3.5:3.8b-mini-instruct-q4\_*K*\_M\`*  
    *\* Cryptographic Model Parent Digest: sha256:\[Parent Hash String from /api/show\]*  
    *\* Quantization Calibration Variable: Q4\_*K*\_M Structural Tuning Profile*  
*\* Secondary Cross-Check Engine (Model M2 Selection Constraints):*  
    *\* Model Label String: NOT\_*APPLICABLE (Tier 3 Host Infrastructure Constraint)  
    \* Dual-Model Validation Cross-Comparison Protocol Status: DEFERRED*\_TIER\_*3

\#\# Verification Registry Signatures  
\* Master Script Manifest Token Verification Array Hash: sha256:\[Hash Target Value\]  
\* Independent Researcher A Codebase Verification Status Result: PASS / FAIL  
\* Independent Researcher B Codebase Verification Status Result: PASS / FAIL

\#\# Context Entry Core Checksum Targets  
\* \`system\_prompt\_v1.txt\`: sha256:\[Cryptographic Hash Return String\]  
\* \`task\_strings\_v1.json\`: sha256:\[Cryptographic Hash Return String\]  
\* \`payload\_approved\_set.json\`: sha256:\[Cryptographic Hash Return String\]  
\* \`capability\_advertisements\_v1.json\`: sha256:\[Cryptographic Hash Return String\]  
\* \[All 9 structural Schema input targets mapped byte-identically here via individual hash fields\]

\#\# Verification Log Commit Signatures  
\* \`phase2\_5\_profiling\_log.jsonl\`: sha256:\[Cryptographic Hash Return String\]  
\* Cross-Researcher Evaluation Input Hash Identity Result: PASS / FAIL  
\* Reconciliation Disagreement Resolution Level Index: \[Count Total / Zero Disagreements\]

\#\# Final Operational Phase Gating Matrix Summary  
\* Final Evaluation Gate Threshold Decision: GO / REVISE  
\* Phase 3 Excluded Scope Elements: \[Listed Operational Exceptions / None\]  
\* Authorization Core Sign-Off:  
    \* Researcher Evaluation Agent A Signature Stamp: \[Field Commit Date\]  
    \* Researcher Evaluation Agent B Signature Stamp: \[Field Commit Date\]  
    \* Research Project Supervisor Clearance Stamp: \[Field Commit Date\]

*End of Phase 2.5 Execution Plan Final Standalone Specification*