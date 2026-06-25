# Schema Validation Report

**Phase:** phase2_infra
**Non-experimental:** true

## Schema Variant Summary

| Variant ID | Density | Condition | File | Hash Recorded |
|------------|---------|-----------|------|---------------|
| D1-CLEAN | 1 | clean_schema | schemas/clean/density1.json | ☐ |
| D3-CLEAN | 3 | clean_schema | schemas/clean/density3.json | ☐ |
| D5-CLEAN | 5 | clean_schema | schemas/clean/density5.json | ☐ |
| D1-POISON-TD | 1 | poisoned_tool_description | schemas/poisoned_tool_description/density1.json | ☐ |
| D3-POISON-TD | 3 | poisoned_tool_description | schemas/poisoned_tool_description/density3.json | ☐ |
| D5-POISON-TD | 5 | poisoned_tool_description | schemas/poisoned_tool_description/density5.json | ☐ |
| D1-POISON-CA | 1 | poisoned_capability_advertisement | schemas/poisoned_capability_advertisement/density1.json | ☐ |
| D3-POISON-CA | 3 | poisoned_capability_advertisement | schemas/poisoned_capability_advertisement/density3.json | ☐ |
| D5-POISON-CA | 5 | poisoned_capability_advertisement | schemas/poisoned_capability_advertisement/density5.json | ☐ |

## Metadata-Only Diff Verification

All clean/poisoned diffs must change ONLY:
- tool descriptions
- parameter documentation
- capability advertisement text

Forbidden changes:
- logical_tool_id
- exposed_tool_name
- parameter names / types / required lists
- tool count
- density level

## Logical ID Mapping

- Tool-name poisoning: **DISABLED** (exposed_tool_name == logical_tool_id)
- Logical IDs stable across all variants: ☐ Yes / ☐ No

## Test Results
- Date:
- Operator:
- pytest output:

## Notes
-
