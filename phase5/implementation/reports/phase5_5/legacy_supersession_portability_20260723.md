# Legacy Supersession Portability

The M1 notebook failed before model execution because its immutable
`phase5_5_campaign_supersession_v1` record stored checkpoint hashes from a
Windows CRLF materialization, while Kaggle validated LF materialization.

The resume validator now accepts the recorded legacy hash when it matches the
same checkpoint JSON under raw, LF, or CRLF bytes. The JSON content remains
hash-bound; changing any non-newline content still fails closed. The v2 path
continues to require its canonical LF checkpoint hashes.

M3 failed the same roster-wide preflight because it audits M1's supersession.
The shared resume fix is therefore propagated to all branches, with M1 and M3
official runners and source freezes regenerated afterward.
