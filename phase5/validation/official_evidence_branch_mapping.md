# Official Evidence Branch Mapping

- Official source tag: `phase5-official-source-v2`
- Official source commit: `c38a339327891b229bcce12d7c04a8a4e6cc63d5`
- Dataset version: `P5-DV-1.0.1-A7C91E42`

| Model slot | Model ID | Evidence branch | Initial remote head |
| --- | --- | --- | --- |
| `M1` | `Qwen/Qwen2.5-7B-Instruct` | `phase5-model-1` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` |
| `M2` | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | `phase5-model-2` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` |
| `M3` | `mistralai/Mistral-7B-Instruct-v0.3` | `phase5-model-3` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` |
| `M4` | `microsoft/Phi-3.5-mini-instruct` | `phase5-model-4` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` |

## Safety Binding

- Checkpoint sync allowlist: `phase5/configs/sync_allowlist.yaml`
- Source paths cannot be staged by checkpoint synchronization.
- Force push, automatic merge, automatic rebase, and unexpected remote divergence are prohibited.
- Remote SHA verification is required after every checkpoint push.
