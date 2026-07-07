# Phase 1: Benchmark Verification, Payload Provenance & MCP Metadata Governance

**Project Title:** Empirical Evaluation of Privilege Aggregation Vulnerabilities in Edge-Deployed Open-Weight Agents via the Model Context Protocol

**Document Status:** Official Phase 1 Protocol Document — Version 1.2

**Dependency:** This document presupposes the approved Phase 0: Threat Model & Scope Lock Memo. All definitions, exclusions, and threat model boundaries established in Phase 0 are inherited without modification. No element of this document supersedes, expands, or narrows the Phase 0 scope.

**Purpose Summary:** This document converts the approved Phase 0 threat model into a source-verified experimental foundation by establishing formal policies for benchmark eligibility, benchmark version control, payload extraction provenance, payload integrity, cryptographic verification, MCP exposure classification, and metadata-poisoning governance. No formal experimental data collection may commence prior to full satisfaction of the Phase 1 success criteria defined in Section 16.

---

## 1. Purpose of Phase 1

Phase 1 exists to convert the approved Phase 0 threat model into a source-verified experimental foundation upon which all subsequent phases may safely build. The approved threat model defines what will be measured and under what conditions; Phase 1 defines where the attack material comes from, how its origin is confirmed, how its integrity is preserved, and how it is formally organized before any contact with the experimental pipeline.

Every element of attack material used in this study — every indirect prompt injection payload, every tool-description poisoning string, every capability-advertisement modification — must be traceable to a named, versioned, publicly accessible benchmark source. Traceability is not an administrative formality; it is the mechanism by which peer reviewers, independent replicators, and future researchers can verify that the attack stimuli used in this study are what the authors claim them to be. Without complete traceability, the study's empirical conclusions rest on an unverifiable evidential base and are therefore unpublishable in indexed academic venues.

The following principles govern the entirety of Phase 1 and may not be overridden by any subsequent phase document:

- **All attack material must be traceable.** Every payload used in experimentation must have a complete, documented chain of custody from its original benchmark source to the payload ledger.
- **All benchmark content must preserve provenance.** The origin, version, extraction date, and human verifier of every benchmark artifact must be recorded before that artifact enters the experimental pipeline.
- **No payload may enter experimentation without verification.** A payload is not eligible for use until it has passed the human verification procedure specified in Section 15 and its cryptographic validation has been recorded in the payload ledger.
- **No benchmark may be used without a documented eligibility decision.** Every candidate benchmark must be processed through the eligibility checklist in Section 4, and a written inclusion or exclusion decision must be recorded before any material is extracted from it.

The necessity of these requirements follows from two converging demands. The first is scientific reproducibility: a study claiming to measure the effect of tool density on privilege aggregation ASR must be reproducible by an independent researcher who can obtain the same attack stimuli, apply them to the same model in the same environment, and expect the same experimental conditions to hold. Reproducibility requires that the attack material be exactly specified, not paraphrased or approximated. The second demand is publishability: journals in the information security domain scrutinize the provenance of attack datasets and payloads with particular care. A manuscript whose methods section cannot precisely identify the source of each attack stimulus, or cannot demonstrate that the extracted stimuli were not modified from their original form, will not survive peer review. Phase 1 exists to make both demands satisfiable. No formal experimental data collection may commence prior to full satisfaction of the Phase 1 success criteria defined in Section 16.

---

## 2. Benchmark Eligibility Requirements

A benchmark is eligible for use in this study only if it satisfies all of the following inclusion criteria. A benchmark that fails any single criterion is ineligible regardless of its academic reputation, citation count, or general relevance to the field of agentic security.

**Criterion 1: The benchmark contains indirect prompt injection scenarios.**
The study investigates indirect prompt injection as the mechanism by which adversarial objectives are introduced into the agent's context. Benchmarks that test only direct prompt injection, jailbreaking, or adversarial prompting without a tool-use or retrieval context do not exercise the attack class under study and are therefore irrelevant as sources of experimental stimuli.

**Criterion 2: The benchmark evaluates tool-using agents.**
The privilege aggregation threat model requires that the agent invoke tools in response to tasks. Benchmarks that evaluate language model behavior in conversation-only settings, without tool invocation, cannot produce the multi-capability coordination events that constitute the dependent variable of this study. Eligible benchmarks must contain evaluation scenarios in which an agent has access to one or more callable tools and is expected to use them to complete tasks.

**Criterion 3: The benchmark's threat assumptions are compatible with Phase 0.**
The Phase 0 Scope Lock Memo defines a specific threat model: benign server, malicious data source, controlled MCP protocol-metadata exposure. A benchmark whose threat assumptions require server-side vulnerabilities, arbitrary malicious server behavior, transitive trust chains, or adaptive attack generation is incompatible with the Phase 0 threat model and may not be used. Compatibility is assessed by comparing the benchmark's documented threat model against the Phase 0 threat model definition and the explicit exclusions listed in Phase 0, Section 3.

**Criterion 4: Static attack examples can be extracted.**
The methodology requires static, immutable payloads fixed prior to experimentation. Benchmarks that generate attacks procedurally, dynamically, or through LLM-based mutators at evaluation time do not produce the stable attack stimuli required for this study's causal design. Eligible benchmarks must contain fixed, documented attack strings or injection scenarios that can be extracted, hashed, and held constant across all experimental trials.

**Criterion 5: Local reproduction is feasible.**
The experimental environment is a single consumer-grade machine operating entirely offline during trials. Benchmarks that require external network access, remote dataset downloads during evaluation, or real-time API calls to external services for evaluation logic are not locally reproducible under the study's hardware and connectivity constraints. Eligibility requires that all benchmark materials necessary for payload extraction and experimental use can be obtained and used from a locally stored copy.

**Criterion 6: No proprietary API access is required.**
The study excludes cloud-hosted LLM APIs and proprietary model evaluation endpoints. Benchmarks whose evaluation scripts, attack-generation pipelines, or scoring logic depend on calls to OpenAI, Anthropic, Google, or equivalent commercial API endpoints are ineligible, because the study cannot reproduce their evaluation conditions without incurring excluded dependencies.

**Criterion 7: Benchmark materials are publicly accessible.**
Benchmark materials must be obtainable from a public repository, published paper supplementary materials, or equivalent openly accessible source without requiring institutional licensing, purchase, or access to a private dataset. Materials that are gated behind access-request processes, paywalls, or institutional agreements introduce traceability risks and prevent independent replication.

**Criterion 8: The benchmark can be represented within an MCP-based workflow without changing attack semantics.**
The experimental environment routes all tool interactions through MCP capability discovery and the FastMCP server interface. For a benchmark payload to be usable, it must be possible to present the payload to the agent through one of the three permitted MCP exposure categories — retrieved content, tool description, or capability advertisement — without modifying the attack's semantic content or intent. Benchmarks whose scenarios are structurally incompatible with MCP representation are ineligible.

---

## 3. Benchmark Exclusion Rules

The following conditions render a benchmark categorically ineligible. These rules exist to prevent scope drift, threat-model corruption, and the introduction of experimental confounds that would undermine causal attribution.

**Exclusion 1: Benchmarks that depend on cloud-only infrastructure.**
Any benchmark whose evaluation process, scoring system, or scenario execution requires cloud compute, remote API calls, or internet-connected services during trials is excluded. The experimental environment is sealed within a local Docker boundary. Cloud dependencies cannot be satisfied without violating the local-execution constraint and introducing uncontrolled variables into the trial environment.

**Exclusion 2: Benchmarks that require proprietary model access.**
Benchmarks designed specifically for evaluation against GPT-4, Claude, Gemini, or other proprietary frontier models are excluded. Such benchmarks may assume response capabilities, context window sizes, function-calling implementations, or behavioral properties specific to those models that do not transfer to open-weight models. Using such benchmarks as stimulus sources risks generating false negatives caused by model incompetence rather than adversarial resilience.

**Exclusion 3: Benchmarks that depend on adaptive attack generation.**
As established in Phase 0, Section 6, adaptive attacks introduce a second independent variable that confounds causal attribution of ASR differences to tool density. Benchmarks whose attack scenarios are generated or modified at evaluation time in response to prior model outputs are incompatible with the static-payload control design.

**Exclusion 4: Benchmarks that require malicious server implementations.**
Phase 0 explicitly excludes server-side taint vulnerabilities and arbitrary malicious server deployments. Benchmarks structured around the premise that the MCP server or tool server has been compromised or reprogrammed to behave adversarially are incompatible with the Phase 0 threat model.

**Exclusion 5: Benchmarks that require real credential theft.**
Phase 0 excludes live credential theft as an adversarial objective. Benchmarks in which attack scenarios are designed to extract functional real-world authentication credentials from live systems are excluded from eligibility. Mock or synthetic credential artifacts used for illustrative purposes within a sandboxed environment are not affected by this exclusion.

**Exclusion 6: Benchmarks that require real-world exfiltration.**
Phase 0 excludes real-world exfiltration. Benchmarks designed to measure whether agents successfully transmit data to live external endpoints, real network destinations, or active third-party services are incompatible with the local, sandboxed experimental environment.

**Exclusion 7: Benchmarks that require transitive-trust environments.**
Phase 0 excludes transitive trust experiments and multi-server trust chains. Benchmarks built around scenarios in which an agent inherits authorization from a remote data source through a chain of systems — such as Git-hosted injection propagation or Sentry event manipulation — require networked multi-system infrastructure incompatible with the local experimental design and outside the approved threat model.

**Exclusion 8: Benchmarks that depend on MCP sampling/createMessage.**
The MCP sampling and createMessage capabilities are explicitly excluded from this study's scope. Benchmarks that exercise these capabilities as part of their attack scenarios are excluded, as the experimental pipeline does not implement these MCP features.

**Exclusion 9: Benchmarks that cannot be reproduced locally.**
Any benchmark whose evaluation cannot be fully executed on the study's local hardware using locally stored materials, without external network access or cloud services, is excluded on grounds of infeasibility.

**Exclusion 10: Benchmarks that cannot be represented in MCP form without changing attack meaning.**
If the semantic content of a benchmark's injection scenario cannot be preserved when adapted to any of the three permitted MCP exposure categories, the benchmark is excluded. Adaptation is permitted only when it changes the delivery mechanism, not the attack intent. Benchmarks whose attack scenarios are structurally incompatible with MCP representation — because their meaning depends on a non-MCP context that cannot be equivalently rendered in an MCP workflow — are ineligible.

---

## 4. Benchmark Verification Checklist

Every candidate benchmark must be processed through the following checklist before any eligibility decision is recorded. The checklist must be completed in full; partial completion does not constitute a valid eligibility review. The completed checklist for each candidate benchmark must be preserved as a permanent component of the Benchmark Verification Report deliverable.

---

### Benchmark Identity

| Field | Value |
|---|---|
| Benchmark Name | |
| Author(s) | |
| Publication Year | |
| Venue / Source | |
| Repository URL | |
| Paper URL | |

All fields are mandatory. A benchmark without a publicly verifiable repository URL and paper URL does not satisfy the public accessibility criterion and must be excluded at this stage.

---

### Benchmark Version Freeze

| Field | Value |
|---|---|
| Benchmark Version (if versioned) | |
| Repository Commit Hash | |
| Access Date | |
| Verification Date | |

**Version freezing is required** because benchmark repositories are living artifacts subject to updates, corrections, additions, and structural reorganization. A benchmark payload extracted from commit A may not exist in commit B, or may have been silently modified between commits. Without a frozen commit hash, the study cannot guarantee that the payloads used in experimentation correspond to the payloads described in the methodology section of the manuscript. Any independent replicator who clones the repository at a later date and obtains a different commit will be unable to verify that their experimental stimuli match those of the original study. Version freezing resolves this ambiguity by making the exact state of the benchmark repository at the time of extraction permanently identifiable and retrievable.

---

### 4.1 Dependency Freeze Record

When benchmark execution depends on external repositories, configuration files, dependency manifests, lockfiles, or version-controlled assets, these artifacts should be recorded whenever reasonably available. Every eligible benchmark must maintain a dependency freeze record tracking:
- Repository Commit Hash
- Dependency Manifest Version (if available)
- Lockfile Version (if available)
- Benchmark Configuration Version (if available)
- Access Date

---

### Threat Model Alignment

| Question | Yes / No / Partial |
|---|---|
| Does the benchmark contain indirect prompt injection scenarios? | |
| Does the benchmark evaluate tool-using agents? | |
| Is the benchmark natively MCP-based? | |
| Is the benchmark MCP-adjacent (compatible without semantic alteration)? | |
| Are static, extractable payloads available? | |
| Is the benchmark compatible with the Phase 0 threat model in full? | |

Any "No" response to the first two rows, or a "No" response to both MCP rows simultaneously, constitutes grounds for exclusion. Partial alignment requires a written justification and must be escalated to the "Include with Limitations" decision category, not the "Include" category.

---

### Experimental Compatibility

| Question | Yes / No |
|---|---|
| Can the benchmark be reproduced locally without internet access? | |
| Are all materials available under an open-source or equivalent public license? | |
| Are the benchmark's evaluation scripts Docker-compatible? | |
| Are the benchmark's scenarios compatible with local open-weight model inference? | |

A "No" response to the first row is a disqualifying exclusion criterion. A "No" to any other row requires a written mitigation plan and escalation to "Include with Limitations."

---

### MCP Compatibility Validation

| Question / Metric | Choice / Value |
|---|---|
| Can benchmark scenarios be represented through MCP capability discovery? | [Yes / No] |
| Can benchmark scenarios be represented through MCP metadata exposure? | [Yes / No] |
| Can all required adaptations be completed without altering attack semantics? | [Yes / No] |
| **MCP Compatible?** | [Yes / No] |
| **Compatibility Justification** | [Written justification summary detailing how attack semantics are maintained under standard runtime mappings] |

A "No" to the third row or the primary compatibility check is a disqualifying exclusion criterion regardless of the responses to other validation metrics. MCP compatibility must be demonstrated clearly without altering baseline benchmark attack semantics.

---

### Final Decision

| Decision | Selected |
|---|---|
| Include | |
| Include with Limitations | |
| Exclude | |

**Written justification is mandatory for every decision.** An inclusion decision must state which threat-model components the benchmark supports and what experimental conditions it will populate. An "Include with Limitations" decision must state precisely which criteria were not fully satisfied, what compensatory measures are in place, and which experimental claims the benchmark cannot support. An exclusion decision must identify the specific criterion or criteria that disqualified the benchmark.

---

## 5. Benchmark Selection Rationale

The selection of benchmark sources for this study must be a documented, criterion-driven process, not an informal judgment. For each benchmark that receives an Include or Include with Limitations decision, the following elements must be formally documented in the Benchmark Selection Rationale Matrix.

**Threat-model alignment:** A precise statement of which components of the Phase 0 threat model the benchmark exercises. This must reference specific Phase 0 threat model elements rather than general assertions of relevance. The documentation must specify whether the benchmark addresses the indirect injection mechanism, the tool-using agent condition, or the capability-advertisement/tool-description poisoning condition, and to what degree.

**Payload quality:** An assessment of the benchmark's payload characteristics relevant to this study: whether payloads are naturally formulated as data-embedded indirect injections, whether they involve multi-tool objectives, whether they can be mapped to privilege aggregation scenarios as defined in Phase 0, and whether they contain sufficient variety across attack families to populate the experimental conditions.

**Reproducibility:** Confirmation that the benchmark's evaluation materials, including all scenarios, injection strings, task definitions, and expected benign behaviors, are locally reproducible from the frozen repository commit without external dependencies.

**Research relevance:** A statement of how the benchmark's scenarios contribute to answering the locked research question. This must be specific: it is not sufficient to assert that a benchmark is well-regarded or widely cited. The documentation must demonstrate that the benchmark's scenarios exercise the specific threat model and the specific dependent variable — privilege aggregation Attack Success Rate as a function of tool density — that this study is designed to measure.

**MCP compatibility:** Confirmation that the benchmark's scenarios can be represented through the permitted MCP exposure categories without semantic alteration, and a specification of which exposure categories each benchmark primarily supports.

**Local deployment feasibility:** Confirmation that all benchmark materials required for payload extraction and experimental use have been obtained, stored locally, and verified against the frozen commit hash.

**Justification of why benchmark popularity alone is not sufficient:** A benchmark's citation count, adoption rate, or community recognition does not constitute evidence of threat-model alignment, payload quality, or MCP compatibility. Many widely used benchmarks in the agentic security literature were designed for cloud-hosted frontier models, use adaptive evaluation logic, or exercise threat models that include server-side vulnerabilities outside the Phase 0 scope. The selection process must demonstrate alignment with this study's specific requirements, not general community endorsement. A benchmark selected on the basis of reputation without documented criterion-based alignment introduces a validity risk that peer reviewers will identify.

---

## 6. Benchmark-to-Research-Question Alignment

Each included benchmark must be formally mapped to the locked research question and its component elements. The mapping must be completed and recorded in the Benchmark-to-Research-Question Mapping Matrix before any payload extraction begins. The purpose of this requirement is to ensure that every piece of benchmark material introduced into the experimental pipeline is there because it directly contributes to answering the research question, not because it is convenient or familiar.

For each included benchmark, the following must be documented:

**Which threat-model component the benchmark exercises:** Each benchmark exercises some subset of the Phase 0 threat model components. The mapping must specify whether the benchmark primarily exercises the indirect prompt injection mechanism, the tool-use agent behavior, the MCP metadata exposure condition, or a combination. Benchmarks that do not map to at least the indirect injection and tool-use components cannot contribute to the primary research question.

**Which MCP exposure categories the benchmark supports:** The three permitted exposure categories — retrieved content, tool description, and capability advertisement — differ in how they present adversarial content to the agent. The mapping must specify which categories each benchmark's scenarios naturally support and which require adaptation. Categories that require adaptation must be flagged for the payload-mapping governance process in Section 12.

**Which privilege-aggregation scenarios the benchmark can represent:** The Phase 0 definition of privilege aggregation requires coordination of two or more distinct capabilities to achieve an adversarial objective. The mapping must identify which benchmark scenarios, by their stated attack objectives, are compatible with this definition — meaning they involve an adversarial goal that requires multi-capability coordination — and which scenarios only support single-tool Hijack Attempt classification.

**Which experimental conditions the benchmark can populate:** The experimental design involves conditions defined by a unique combination of tool density level, adversarial framing condition, and injection context. The mapping must specify which conditions each benchmark can contribute payloads to, based on its threat-model coverage. A benchmark that can populate only one experimental condition is not excluded on that basis, but its limited scope must be documented.

The requirement that benchmarks contribute directly to the research objective exists because the alternative — selecting benchmarks and then constructing research questions around their available content — inverts the scientific process and introduces a form of undeclared post-hoc experimental design. Benchmarks are instruments. Like all instruments, they must be validated against the measurement objective before use.

---

## 7. Payload Provenance Policy

Provenance refers to the complete, documented chain of origin for every payload from its first appearance in a benchmark source to its use in the experimental pipeline. Provenance is mandatory for every payload without exception.

Every payload admitted to the payload ledger must record the following provenance fields:

| Field | Definition |
|---|---|
| **Payload ID** | A unique alphanumeric identifier assigned at extraction, used to reference the payload in all subsequent documents, logs, and analysis outputs. The Payload ID must not change after assignment. |
| **Source Benchmark** | The full name of the benchmark from which the payload was extracted, as it appears in the Benchmark Verification Report. |
| **Source File** | The exact relative file path within the frozen benchmark repository from which the payload was extracted (e.g., `tasks/injection/email_phishing.json`). |
| **Original Location** | The specific location within the source file where the payload text was found — for example, a JSON key name, a line number range, or a named field in a structured scenario object. |
| **Original Identifier** | The identifier used by the benchmark to reference this scenario or payload, if one exists — for example, a task ID, scenario number, or attack-category label assigned by the benchmark authors. |
| **Original Attack Category** | The attack category, attack type, or scenario label assigned to this payload by the benchmark authors in their documentation or source code. |
| **Original Text** | The complete, unmodified payload text as it appears in the source file at the frozen commit. No character, whitespace element, or formatting mark may be altered from the original. |
| **Extraction Date** | The calendar date on which the payload was extracted from the local copy of the frozen benchmark repository. |
| **Human Verifier** | The full name of the researcher who performed the human verification procedure specified in Section 15 for this payload. |

No payload may exist in the payload ledger without all nine provenance fields populated. A payload with incomplete provenance is treated as unverified and may not enter the experimental pipeline.

---

## 8. Payload Integrity Requirements

The semantic content of benchmark payloads must remain unchanged from the moment of extraction to the moment of use in the experimental pipeline. MCP integration may require controlled transformations that produce a derived runtime payload. Permitted examples include:
* Tool-name substitution
* Placeholder replacement
* Environment-specific references

Such transformations are permitted only when the attack intent remains unchanged, the attack objectives remain completely unchanged, and the original benchmark meaning remains fully intact. All transformations must be formally documented in the ledger. Semantic preservation—not byte-for-byte identity—is the governing principle for payload modification under this protocol.

The following actions are **strictly prohibited**:

- **Rewriting attack intent:** The adversarial objective of a payload — what it instructs or attempts to coerce the agent into doing — may not be changed, softened, amplified, or redirected.
- **Altering attack objectives:** If a benchmark payload targets a specific capability (e.g., accessing a calendar tool), that target may not be changed to a different capability on the grounds that the experimental environment uses a different tool schema.
- **Changing attack semantics:** The meaning of the payload's adversarial content — the implicit or explicit instruction it contains — must be preserved in full.
- **AI-generated content substitution:** No language model, including the research models used in experimental trials, may be used to generate replacement, paraphrase, extension, or "cleaned-up" versions of benchmark payloads. AI-generated attack content is explicitly excluded from this study by the Phase 0 scope.
- **Author-generated attack fabrication:** The researcher may not compose original injection payloads, insert new adversarial content, or supplement benchmark material with self-authored attack strings, regardless of how closely such strings resemble the benchmark's style or content.

All adaptations of any kind must be documented in the provenance ledger entry for the affected payload. The documentation must record: the original text, the adapted text, the category of adaptation (tool-name substitution, placeholder replacement, or environment-specific reference), and the written justification for why the adaptation was required and how it preserves attack semantics.

---

## 9. Cryptographic Verification Procedure

Every payload admitted to the payload ledger must be cryptographically verified according to the following procedure. The procedure must be completed in full before the payload's hash is recorded. A payload whose hash was generated from a source other than the verbatim original text as it appears in the frozen benchmark repository is invalid and must be regenerated.

The experimental protocol implements a formal Dual-Hash Architecture to eliminate ambiguity between the source data and modified variants. The following definitions govern hash tracking:
* **Source Payload Hash:** The SHA-256 hash computed from the original benchmark payload exactly as extracted from the source benchmark. Its purpose is to preserve provenance and verify source integrity.
* **Adapted Payload Hash:** The SHA-256 hash computed from the MCP-adapted payload actually used during experimentation. Its purpose is to preserve the exact reproducibility of the runtime artifact.

The Source Payload Hash and Adapted Payload Hash may differ whenever a permitted MCP adaptation has occurred. Both hashes must be explicitly recorded in the experimental logs.

**Step 1 — Payload extraction.** Open the local copy of the frozen benchmark repository at the recorded commit. Navigate to the source file identified in the provenance record. Locate the payload at the original location and original identifier specified in the provenance record. Copy the complete payload text without modification.

**Step 2 — Human verification against source.** Before generating any hash, the human verifier must perform the visual and semantic verification procedure defined in Section 15. This step confirms that the extracted text matches the source exactly and that the provenance fields are correctly recorded. Cryptographic verification does not substitute for human verification; both are required.

**Step 3 — SHA-256 hash generation.** Generate the Source Payload Hash of the extracted payload text using a locally executed cryptographic utility. If an adaptation occurs, generate the Adapted Payload Hash from the finalized payload string using the same utility. Both operations must be performed locally; no external hashing services may be used.

**Step 4 — Hash recording.** Record the generated Source Payload Hash and Adapted Payload Hash in the payload hash ledger under their corresponding IDs as the authoritative integrity references. Any subsequent copy of the payload used in the experimental pipeline must produce matching structural hashes. If a copy produces a different hash, the discrepancy indicates modification and must be investigated and resolved before the payload is used.

**Step 5 — Verification-log creation.** Create an entry in the verification log recording: the Payload ID, the extraction date, the hash generation date, the name of the human verifier, and the cryptographic hash values. The verification log is a permanent record; entries may not be deleted or overwritten.

---

### 9.1 Payload Normalization Policy

Prior to the generation of any cryptographic hash, all payload text must pass through a strict normalization process. This policy ensures that minor environment variations do not introduce semantic-free hash discrepancies:
* **Encoding:** All payloads must be explicitly encoded using the UTF-8 format.
* **Unicode Normalization:** Unicode normalization rules (NFC) must be applied and fully documented to resolve equivalent character representations.
* **Line Endings:** Line endings must be normalized consistently across all platforms to standard Unix format (`\n`).
* **Whitespace:** The whitespace truncation and spacing policy must be documented and executed uniformly.

This normalization procedure must be applied consistently to both source and adapted payloads. It is a necessary mechanism for reproducible cryptographic verification, ensuring that hashes vary strictly due to intentional text modifications rather than accidental runtime formatting differences.

---

## 10. MCP Exposure Classification Framework

Every payload in the payload ledger must be assigned to one or more MCP exposure categories. The exposure category specifies the mechanism by which the adversarial content is presented to the agent within the MCP experimental workflow. The following three categories constitute the complete approved classification for this study. No additional exposure categories may be introduced without a formal scope-amendment process.

---

### Retrieved Content

The payload appears within material that the agent retrieves during task execution through a read-access tool. The agent is assigned a benign task that requires it to invoke a tool to read a document, file, report, note, or equivalent text-bearing artifact. The adversarial content is embedded within the text of that artifact and enters the agent's context window as data rather than as metadata.

The Retrieved Content category corresponds to the classical formulation of indirect prompt injection: the agent encounters adversarial content as a side effect of performing a legitimate data-retrieval action. This category is fundamental to the study because it exercises the core mechanism — agent reads data, data contains injection, agent may be redirected — that the indirect prompt injection literature has established as the primary cognitive attack surface.

---

### Tool Description

The payload appears within the MCP tool-description metadata field of a discoverable tool. Tool descriptions are presented to the agent during MCP capability discovery as part of the tool schema. The agent reads tool descriptions in order to understand what each tool does, what parameters it accepts, and when it should be invoked. Adversarial content placed within a tool description is processed by the agent as part of its contextual understanding of the tool's function.

This category constitutes the MCP-native protocol-metadata poisoning condition required by the Phase 0 threat model. It exercises the capability advertisement surface identified in Phase 0 as the permitted MCP-native attack mechanism and is essential for the study's claim to be investigating MCP-specific cognitive vulnerabilities rather than generic tool-calling behavior.

---

### Capability Advertisement

The payload appears within the capability advertisement metadata presented to the agent during the MCP capability discovery handshake. This category is distinct from Tool Description in that it targets the higher-level capability declaration rather than the individual tool's description field. Capability advertisements may include server-level capability claims, tool-category declarations, or aggregate metadata that contextualizes the agent's understanding of what class of operations is available.

This category provides the second MCP-native protocol-metadata condition and, together with the Tool Description category, constitutes the study's empirical contribution to the literature on MCP capability-discovery manipulation.

---

### 10.1 Exposure-Specific Reporting Requirement

Exposure categories represent distinct experimental contexts and must be treated as separate analytical conditions during later experimental phases. Consequently, downstream results obtained from Retrieved Content, Tool Description, and Capability Advertisement should not automatically be aggregated into a single metric without explicit methodological justification. 

This segregation is mandatory because different exposure categories may fundamentally differ in their baseline trust assumptions, cognitive influence profiles, agent decision-making behaviors, and capability-discovery effects. Therefore, they must be evaluated independently unless aggregation is explicitly justified.

---

## 11. MCP Metadata-Poisoning Governance Rules

The metadata-poisoning condition defined in Phase 0 is subject to strict governance rules that ensure any observed effect of metadata manipulation can be attributed to the metadata content rather than to any other change in the experimental environment. These rules derive directly from the causal attribution requirements of the Phase 0 threat model.

**Only metadata may vary between the clean baseline condition and any metadata-poisoning condition.** The following metadata fields are the sole permitted sources of variation:
- Tool names
- Tool descriptions
- Capability advertisements
- Parameter documentation

All other elements of the experimental environment must be identical between the baseline and poisoning conditions within the same density level. This means that the number and type of tools, the tool execution logic, the system prompt, the benign task specification, the payload delivery mechanism for non-metadata conditions, and the logging infrastructure must be held constant.

The following elements are **forbidden from variation** between baseline and metadata-poisoning conditions:
- **Server implementation:** The FastMCP server code is fixed across all conditions. No modification to server-side Python files, route handlers, or server configuration is permitted between conditions.
- **Tool logic:** The computational operations performed by each tool are identical in the baseline and poisoning conditions.
- **Tool behavior:** The inputs each tool accepts, the outputs it produces, and the errors it raises are identical across all conditions.
- **Tool outputs:** The mock data returned by tools in response to invocations is fixed by the experimental design.
- **Logging infrastructure:** The logging system and grading pipeline are identical across all conditions.

---

## 12. Payload-to-MCP Mapping Framework

Benchmark payloads were designed for evaluation contexts that may differ structurally from the MCP experimental workflow used in this study. The mapping framework defines the conditions under which a benchmark payload may be adapted for MCP delivery and the constraints that govern all adaptation decisions.

**Adaptation means changing only the exposure location.** When a benchmark payload designed for delivery via a web-browsing tool is adapted for delivery via an MCP file-read tool, the adaptation consists of changing where the payload appears — from a mock webpage to a mock document — without changing what the payload says or what it instructs the agent to do.

**Adaptation does NOT permit:**
- **Semantic modification:** The meaning of the adversarial directive may not change as a result of adaptation.
- **Attack-objective modification:** The goal of the adversarial action must be preserved across the adaptation.
- **Payload rewriting:** The payload text may not be rewritten for any reason other than the minimum-necessary substitutions defined in Section 8.
- **Benchmark reinterpretation:** The researcher may not decide that a benchmark payload "really means" something different from what its original documentation states.

---

## 13. Preliminary Payload Classification Framework

The preliminary classification framework provides an organizational structure for bookkeeping and dataset management during Phase 1. It does not modify the Phase 0 threat model, does not define experimental outcome categories, and does not constitute the final taxonomy used in experimental grading, which is defined in later phase documents. Its sole purpose is to enable the orderly organization of the payload ledger.

Payloads extracted from eligible benchmarks are assigned to one of the following preliminary classification categories based on their primary adversarial mechanism as documented in the source benchmark:
- **Instruction Override:** Payloads whose primary mechanism is the direct issuance of an instruction to the agent within retrieved data or metadata, directing the agent to perform a specific action superseding or contradicting its assigned task.
- **Cross-Capability Escalation:** Payloads whose primary mechanism involves directing the agent to invoke a capability beyond the one required for the benign task, specifically in conjunction with another available capability.
- **Data Access and Exfiltration:** Payloads whose adversarial objective involves unauthorized reading, copying, or transmission of data.
- **Other Benchmark-Defined Categories:** Payloads that fall under a category defined in the source benchmark's own taxonomy but that do not map cleanly to the three categories above.

---

## 14. Payload Ledger Schema

The payload ledger is the master record of all attack material admitted to the experimental pipeline. Every payload must have a complete ledger entry before it may be used in any experimental trial. The ledger is a permanent, immutable record; entries may be added but never deleted or silently modified.

The payload ledger schema mandates the following tracking fields:

| Field | Purpose |
|---|---|
| **Payload ID** | The unique identifier assigned at extraction. Used as the primary key across cross-references. |
| **Source Payload ID** | The unique identifier of the benchmark-extracted payload. |
| **Adapted Payload ID** | The unique identifier of the MCP-runtime payload. |
| **Adaptation Type** | Categorization of the transformation performed (`Tool-name substitution`, `Placeholder replacement`, `Environment reference substitution`). |
| **Adaptation Justification** | A formal explanation of why the transformation was necessary for the local implementation to maintain traceability. |
| **Verification Status** | Governance track status tracking artifact validation step progress state (`Extracted`, `Source Verified`, `Hash Verified`, `Adaptation Verified`, `Approved for Experimentation`). |
| **Runtime Payload Version** | A version identifier mapping the payload directly to its active experimental release. |
| **Runtime Provenance Notes** | Complete technical documentation of runtime-specific adaptations, environment variables, and specific local deployment details. |
| **Source Benchmark** | The full benchmark name as listed in the Benchmark Verification Report. |
| **Source File** | The exact relative path within the frozen benchmark repository to the file from which this payload was extracted. |
| **Source Location** | The specific location within the source file where the payload text was found. |
| **Benchmark Version** | The benchmark version identifier, if applicable. |
| **Repository Commit Hash** | The full commit hash of the frozen repository state at the time of extraction. |
| **Source Payload Hash** | SHA-256 integrity hash derived directly from raw extracted source materials. |
| **Adapted Payload Hash** | SHA-256 runtime validation hash mapping directly to post-adaption configurations. |
| **Exposure Category** | The MCP exposure category assigned to this payload entry. |
| **Preliminary Classification** | The preliminary classification assigned from the framework in Section 13. |
| **Expected Benign Behavior** | A precise specification of the tool-call sequence the agent is expected to produce when completing the benign task under clean conditions. |
| **Forbidden Behavior** | A precise specification of the tool-call action that constitutes an adversarial success for this payload. |
| **Aggregation Requirement** | A binary field specifying whether this payload requires coordination of two or more tools. |
| **Required Tools** | The list of tool names from the experimental mock schema that the payload's adversarial objective requires. |
| **Human Verifier** | The full name of the researcher who completed the Section 15 human verification procedure. |
| **Verification Date** | The calendar date on which human verification was completed. |

All fields are mandatory. A ledger entry with any blank field is incomplete and unapproved for experimental use.

---

## 15. Human Verification Requirements

Human verification is a mandatory component of the payload admission process. No automated tool, AI assistant, language model, or script may perform human verification or certify the accuracy of provenance records in place of a human researcher.

The human researcher performing verification must complete the following procedure for every payload:

**Step 2 — Verify payload text manually.** Read the payload text in the source file and complete a manual verification sufficient to confirm textual identity and provenance, supported by cryptographic hash validation. Confirm that the data accurately represents the benchmark domain. If any discrepancy is found, the ledger entry must be corrected before proceeding, and the cryptographic hash sequence must be completely regenerated.

**Step 3 — Verify benchmark provenance.** Confirm that all baseline file paths, indices, and meta elements correctly match the source system state. Verify that the Repository Commit Hash matches the commit currently checked out in the local repository.

**Step 4 — Verify classification.** Confirm that the Preliminary Classification assigned to the payload corresponds to the adversarial mechanism visible in the original payload text.

**Step 5 — Verify exposure-category assignment.** Confirm that the Exposure Category assigned to the payload is compatible with the payload's content and the adaptation documented in the provenance record.

**Step 6 — Verify the recorded hash.** Independently regenerate the Source Payload Hash and Adapted Payload Hash using a local cryptographic utility to confirm the entries in the ledger match perfectly.

---

### 15.1 Automation-Assisted Verification Support

Deterministic automation utilities may be employed to optimize and scale the administrative stages of the payload ingestion pipeline. Specifically, deterministic automation may assist with payload extraction, provenance recording, SHA-256 generation, ledger population, and cross-field consistency checking. 

Explicitly, automated systems are strictly prohibited from performing any regulatory or evaluative tasks. Automation may not certify provenance accuracy, approve benchmark eligibility, approve payload inclusion, or approve exposure classifications, and it cannot replace required human review. Human researchers remain solely responsible for the final certification of protocol compliance, provenance accuracy, and payload eligibility.

---

## 16. Phase 1 Success Criteria

Phase 1 is complete, and formal implementation phases may begin, only when all of the following conditions have been satisfied and documented. The satisfaction of each condition must be verifiable by reference to a specific Phase 1 deliverable.

- **Benchmark eligibility decisions are finalized.** Every candidate benchmark considered for this study has been processed through the full verification checklist in Section 4.
- **Benchmark versions are frozen.** Every included benchmark has a recorded repository commit hash, access date, and verification date in the Register.
- **Benchmark selection rationale is documented.** The Selection Rationale Matrix contains a complete entry for every included benchmark.
- **Benchmark-to-research-question mappings are completed.** The Mapping Matrix contains a complete entry for every included benchmark.
- **Payload provenance is recorded.** Every payload admitted to the payload ledger has complete provenance records covering all metrics.
- **Cryptographic hashes are generated and recorded.** Dual-hash structures (Source and Adapted payload hashes) are generated from normalized strings and recorded.
- **Exposure categories are assigned.** Every payload in the payload ledger has been assigned to at least one of the three permitted MCP exposure categories.
- **Metadata-governance rules are finalized.** The Metadata-Poisoning Governance Rules document contains a complete specification of permitted metadata variation fields.
- **Payload ledger is completed.** Every payload admitted to the experimental pipeline has a complete ledger entry with all fields populated as specified in Section 14.
- **Human verification is completed.** Every payload in the payload ledger has been processed through the verification procedure in Section 15.

No formal experimental data collection may begin before Phase 1 completion because the experimental pipeline's correctness, reproducibility, and publishability all depend on a verified, provenance-complete payload set. This restriction explicitly permits foundational preparatory actions, including Docker setup, FastMCP prototyping, logging validation, feasibility testing, and general infrastructure development, provided that no official experimental results are collected.

---

## 17. Phase 1 Deliverables

The following documents constitute the complete set of Phase 1 outputs. All deliverables must be completed and internally consistent before Phase 1 is declared complete.

- **Benchmark Verification Report:** A document containing the completed Section 4 verification checklist for every candidate benchmark reviewed during Phase 1.
- **Benchmark Inclusion/Exclusion Matrix:** A summary table listing every candidate benchmark, its final eligibility decision, and the primary criterion that drove the decision.
- **Benchmark Version Freeze Register:** A document recording, for every included benchmark, the repository commit hash, benchmark version, access date, and verification date.
- **Benchmark Selection Rationale Matrix:** A table documenting the six required rationale dimensions for every included benchmark.
- **Benchmark-to-Research-Question Mapping Matrix:** A structured document mapping each included benchmark to specific threat-model components, MCP exposure categories, privilege-aggregation scenario types, and experimental conditions.
- **Payload Provenance Ledger:** A complete record of all provenance fields for every payload admitted to the experimental pipeline, as specified in Section 14.
- **Payload Hash Ledger:** A document recording the Payload ID and cryptographic dual hashes (Source and Adapted) for every payload in the provenance ledger.
- **MCP Exposure Classification Ledger:** A document recording the exposure category assignment for every payload, with documentation of any adaptations made for MCP integration.
- **Metadata-Poisoning Governance Rules:** A finalized document specifying the permitted and forbidden sources of variation in metadata-poisoning experimental conditions, as defined in Section 11.
- **Human Verification Checklist:** A completed form for every payload recording the verification steps performed, the name of the human verifier, and the verification date.

---

*This document is operative upon completion of all Phase 1 success criteria. Formal experimental data collection phases may not begin until the Phase 1 Deliverables are complete and internally consistent.*