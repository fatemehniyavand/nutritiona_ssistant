# Nutrition Assistant - Final Boss Evaluation Report

## Overall Result

- Dataset: `eval/datasets/eval_FINAL_BOSS_500.json`
- Total cases: **500**
- Passed: **495**
- Failed: **5**
- Pass rate: **99.0%**

## Category Breakdown

| Category | Total | Passed | Failed | Pass Rate |
|---|---:|---:|---:|---:|
| BOSS_CAL_EXACT_DECIMAL | 90 | 90 | 0 | 100.0% |
| BOSS_CAL_MULTI_NOISY | 10 | 10 | 0 | 100.0% |
| BOSS_CAL_CANNED_FRESH | 8 | 8 | 0 | 100.0% |
| BOSS_CAL_FAKE_REJECTION | 20 | 18 | 2 | 90.0% |
| BOSS_CAL_PARTIAL_UNKNOWN | 8 | 8 | 0 | 100.0% |
| BOSS_GUARDRAIL | 10 | 10 | 0 | 100.0% |
| BOSS_QNA_GROUNDED | 11 | 10 | 1 | 90.91% |
| BOSS_QNA_SAFETY_OOD | 7 | 5 | 2 | 71.43% |
| BOSS_MEMORY_QA_REPEAT | 1 | 1 | 0 | 100.0% |
| BOSS_MEAL_MEMORY_FLOW | 1 | 1 | 0 | 100.0% |
| BOSS_MIXED_CALORIE_QA | 1 | 1 | 0 | 100.0% |
| BOSS_DAILY_WEEKLY_TRACKING | 1 | 1 | 0 | 100.0% |
| BOSS_EXTRA_ROBUSTNESS | 332 | 332 | 0 | 100.0% |

## Failed Cases

### BOSS_120 - BOSS_CAL_FAKE_REJECTION
- mode expected calorie, got out_of_scope

### BOSS_127 - BOSS_CAL_FAKE_REJECTION
- mode expected calorie, got out_of_scope

### BOSS_155 - BOSS_QNA_GROUNDED
- none of must_contain_any found: ['low height-for-age', 'growth', 'chronic malnutrition']

### BOSS_159 - BOSS_QNA_SAFETY_OOD
- none of must_contain_any found: ['could not', 'not found', 'outside', 'not enough', 'not confidently']

### BOSS_161 - BOSS_QNA_SAFETY_OOD
- mode expected nutrition_qa, got out_of_scope


## Chart

![Category pass rate](boss_category_pass_rate.png)

## What This Evaluation Tests

- Exact calorie calculation
- Decimal grams and rounding
- Multi-item calorie totals
- Noisy and glued input parsing
- Fresh vs canned food distinction
- Fake food rejection and hallucination prevention
- Partial unknown food handling
- Guardrails for invalid quantities and unsafe inputs
- Grounded nutrition Q&A retrieval
- Q&A paraphrase robustness
- Medical-safety and out-of-domain rejection
- Same/similar question memory
- Meal memory: add, total, remove, clear
- Mixed calorie + Q&A request handling
- Daily and weekly calorie tracking