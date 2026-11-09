# agent-telephone — Claude Code pilot, scored

- 853 valid runs, 6403 messages, 134298 scored units (note view), 853 endpoint evaluations.
- Judge: gpt-6.1-sol via codex, passes ['note/0', 'full/0', 'note/1']; pass 0 vs 1 κ = 0.927 (n = 14434)

## Survival by distance (note view; source, downward non-forward hand-offs, endpoint)

| kind | distance | scored | survival | lost_rate | distorted_rate | inverted_rate | unscored |
|---|---|---|---|---|---|---|---|
| endpoint | 4 | 4501 | 0.800 | 0.077 | 0.123 | 0.000 | 0 |
| endpoint | 5 | 13409 | 0.745 | 0.165 | 0.084 | 0.006 | 0 |
| handoff | 2 | 11992 | 0.955 | 0.004 | 0.037 | 0.003 | 0 |
| handoff | 3 | 6027 | 0.949 | 0.007 | 0.041 | 0.003 | 0 |
| handoff | 4 | 8941 | 0.865 | 0.080 | 0.052 | 0.003 | 0 |
| source | 1 | 17910 | 0.962 | 0.000 | 0.028 | 0.010 | 0 |

## Survival by information distance (hand-offs, note view)

| kind | info_distance | scored | survival | lost_rate | distorted_rate | inverted_rate |
|---|---|---|---|---|---|---|
| handoff | 2 | 17957 | 0.926 | 0.027 | 0.044 | 0.003 |
| handoff | 3 | 6027 | 0.949 | 0.007 | 0.041 | 0.003 |
| handoff | 4 | 2976 | 0.862 | 0.094 | 0.039 | 0.005 |

## Hand-off survival by fact type (note view; downward, non-forward)

| fact_type | distance | scored | survival | lost_rate | distorted_rate | inverted_rate |
|---|---|---|---|---|---|---|
| conditional | 2 | 1334 | 0.978 | 0.000 | 0.003 | 0.019 |
| conditional | 3 | 670 | 0.970 | 0.000 | 0.012 | 0.018 |
| conditional | 4 | 1048 | 0.895 | 0.004 | 0.082 | 0.019 |
| low_salience | 2 | 1429 | 0.966 | 0.000 | 0.034 | 0.000 |
| low_salience | 3 | 718 | 0.964 | 0.000 | 0.036 | 0.000 |
| low_salience | 4 | 1143 | 0.964 | 0.008 | 0.028 | 0.000 |
| name | 2 | 2096 | 0.932 | 0.000 | 0.068 | 0.000 |
| name | 3 | 1053 | 0.925 | 0.005 | 0.070 | 0.000 |
| name | 4 | 1571 | 0.904 | 0.030 | 0.066 | 0.000 |
| negation | 2 | 1809 | 0.990 | 0.001 | 0.003 | 0.007 |
| negation | 3 | 909 | 0.987 | 0.000 | 0.008 | 0.006 |
| negation | 4 | 1380 | 0.982 | 0.002 | 0.012 | 0.004 |
| number | 2 | 3040 | 0.957 | 0.001 | 0.041 | 0.000 |
| number | 3 | 1529 | 0.956 | 0.001 | 0.043 | 0.000 |
| number | 4 | 2087 | 0.920 | 0.019 | 0.060 | 0.000 |
| priority | 2 | 1142 | 0.970 | 0.000 | 0.030 | 0.000 |
| priority | 3 | 574 | 0.972 | 0.000 | 0.028 | 0.000 |
| priority | 4 | 856 | 0.849 | 0.098 | 0.053 | 0.000 |
| rationale | 2 | 1142 | 0.882 | 0.040 | 0.078 | 0.000 |
| rationale | 3 | 574 | 0.847 | 0.064 | 0.089 | 0.000 |
| rationale | 4 | 856 | 0.317 | 0.616 | 0.068 | 0.000 |

## Hand-off survival by model (note view; downward, non-forward)

| model | distance | scored | survival | lost_rate | distorted_rate | inverted_rate |
|---|---|---|---|---|---|---|
| haiku | 2 | 6048 | 0.942 | 0.008 | 0.046 | 0.004 |
| haiku | 3 | 3024 | 0.936 | 0.011 | 0.050 | 0.004 |
| haiku | 4 | 4512 | 0.845 | 0.090 | 0.061 | 0.004 |
| sonnet | 2 | 5944 | 0.969 | 0.001 | 0.029 | 0.002 |
| sonnet | 3 | 3003 | 0.962 | 0.003 | 0.032 | 0.002 |
| sonnet | 4 | 4429 | 0.886 | 0.069 | 0.043 | 0.002 |

## Hand-off survival by format (note view; free vs structured)

| handoff_format | distance | scored | survival | lost_rate | distorted_rate | inverted_rate |
|---|---|---|---|---|---|---|
| free | 2 | 6005 | 0.956 | 0.004 | 0.037 | 0.003 |
| free | 3 | 3003 | 0.941 | 0.011 | 0.045 | 0.003 |
| free | 4 | 4490 | 0.851 | 0.092 | 0.054 | 0.003 |
| structured | 2 | 5987 | 0.955 | 0.005 | 0.038 | 0.003 |
| structured | 3 | 3024 | 0.957 | 0.003 | 0.037 | 0.002 |
| structured | 4 | 4451 | 0.879 | 0.068 | 0.050 | 0.003 |

## Upward hand-backs (note view)

| topology | distance | scored | survival | lost_rate | distorted_rate | inverted_rate |
|---|---|---|---|---|---|---|
| hier_chain | 4 | 4501 | 0.800 | 0.077 | 0.123 | 0.000 |
| hier_chain | 5 | 8965 | 0.773 | 0.132 | 0.090 | 0.005 |
| hier_chain | 6 | 8954 | 0.775 | 0.131 | 0.091 | 0.002 |
| hier_chain | 7 | 4464 | 0.745 | 0.192 | 0.059 | 0.004 |
| hier_chain | 8 | 4464 | 0.744 | 0.192 | 0.060 | 0.004 |
| hub_relay | 3 | 8945 | 0.889 | 0.058 | 0.050 | 0.003 |
| hub_relay | 5 | 8945 | 0.752 | 0.147 | 0.097 | 0.004 |
| hub_relay | 6 | 8934 | 0.756 | 0.144 | 0.097 | 0.002 |

## Forward notes: contradiction of the attached original (note view)

| model | direction | distance | n | scored | contradicted | contradiction_rate | noise_reading | silent_rate |
|---|---|---|---|---|---|---|---|---|
| haiku | down | 2 | 3024 | 3024 | 46 | 0.015 | 3 | 0.744 |
| haiku | down | 3 | 1512 | 1512 | 84 | 0.056 | 9 | 0.312 |
| haiku | down | 4 | 2256 | 2256 | 142 | 0.063 | 26 | 0.178 |
| haiku | up | 3 | 1512 | 1512 | 74 | 0.049 | 17 | 0.078 |
| haiku | up | 4 | 768 | 768 | 78 | 0.102 | 9 | 0.081 |
| haiku | up | 5 | 3024 | 3024 | 248 | 0.082 | 42 | 0.133 |
| haiku | up | 6 | 3024 | 3024 | 257 | 0.085 | 42 | 0.130 |
| haiku | up | 7 | 744 | 744 | 31 | 0.042 | 11 | 0.183 |
| haiku | up | 8 | 744 | 744 | 34 | 0.046 | 11 | 0.180 |
| sonnet | down | 2 | 2894 | 2894 | 82 | 0.028 | 9 | 0.628 |
| sonnet | down | 3 | 1426 | 1426 | 47 | 0.033 | 17 | 0.154 |
| sonnet | down | 4 | 2212 | 2212 | 97 | 0.044 | 34 | 0.149 |
| sonnet | up | 3 | 1468 | 1468 | 58 | 0.040 | 17 | 0.070 |
| sonnet | up | 4 | 682 | 682 | 68 | 0.100 | 7 | 0.076 |
| sonnet | up | 5 | 2894 | 2894 | 216 | 0.075 | 45 | 0.136 |
| sonnet | up | 6 | 2894 | 2894 | 209 | 0.072 | 45 | 0.133 |
| sonnet | up | 7 | 744 | 744 | 36 | 0.048 | 13 | 0.159 |
| sonnet | up | 8 | 744 | 744 | 36 | 0.048 | 13 | 0.163 |

## Noise propagation (asr variants, note view)

| noise_kind | kind | distance | flagged | freeze | amplify | repair | lost | drift |
|---|---|---|---|---|---|---|---|---|
| asr_name | endpoint | 4 | 0 | 86 | 0 | 0 | 0 | 0 |
| asr_name | endpoint | 5 | 0 | 187 | 0 | 0 | 6 | 2 |
| asr_name | handoff | 2 | 0 | 196 | 0 | 9 | 75 | 1 |
| asr_name | handoff | 3 | 10 | 218 | 34 | 4 | 15 | 0 |
| asr_name | handoff | 4 | 6 | 231 | 32 | 4 | 7 | 1 |
| asr_name | handoff | 5 | 2 | 267 | 4 | 0 | 6 | 2 |
| asr_name | handoff | 6 | 5 | 263 | 5 | 0 | 6 | 2 |
| asr_name | handoff | 7 | 0 | 48 | 4 | 0 | 2 | 0 |
| asr_name | handoff | 8 | 0 | 48 | 4 | 0 | 2 | 0 |
| homophone | endpoint | 4 | 0 | 21 | 0 | 5 | 12 | 16 |
| homophone | endpoint | 5 | 0 | 93 | 0 | 40 | 10 | 19 |
| homophone | handoff | 2 | 15 | 118 | 4 | 15 | 38 | 26 |
| homophone | handoff | 3 | 26 | 89 | 45 | 23 | 7 | 26 |
| homophone | handoff | 4 | 4 | 79 | 47 | 39 | 13 | 34 |
| homophone | handoff | 5 | 4 | 100 | 16 | 44 | 17 | 35 |
| homophone | handoff | 6 | 6 | 109 | 17 | 33 | 17 | 34 |
| homophone | handoff | 7 | 2 | 32 | 6 | 14 | 0 | 0 |
| homophone | handoff | 8 | 2 | 32 | 6 | 14 | 0 | 0 |
| punct | endpoint | 4 | 0 | 1 | 0 | 49 | 0 | 4 |
| punct | endpoint | 5 | 0 | 20 | 0 | 105 | 1 | 34 |
| punct | handoff | 2 | 0 | 34 | 0 | 118 | 42 | 20 |
| punct | handoff | 3 | 4 | 50 | 0 | 140 | 3 | 17 |
| punct | handoff | 4 | 2 | 34 | 0 | 150 | 2 | 26 |
| punct | handoff | 5 | 1 | 21 | 0 | 152 | 1 | 39 |
| punct | handoff | 6 | 1 | 21 | 0 | 151 | 2 | 39 |
| punct | handoff | 7 | 0 | 8 | 0 | 33 | 1 | 12 |
| punct | handoff | 8 | 0 | 9 | 0 | 32 | 1 | 12 |

By model (all distances):

| noise | model | kind | flagged | freeze | amplify | repair | lost | drift |
|---|---|---|---|---|---|---|---|---|
| asr_approver | haiku | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| asr_approver | haiku | handoff | 0 | 82 | 21 | 0 | 5 | 0 |
| asr_approver | sonnet | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| asr_approver | sonnet | handoff | 0 | 83 | 19 | 0 | 6 | 0 |
| asr_av | haiku | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| asr_av | haiku | handoff | 11 | 70 | 1 | 0 | 8 | 0 |
| asr_av | sonnet | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| asr_av | sonnet | handoff | 6 | 72 | 6 | 0 | 6 | 0 |
| asr_cfo | haiku | endpoint | 0 | 34 | 0 | 0 | 1 | 1 |
| asr_cfo | haiku | handoff | 2 | 148 | 4 | 8 | 16 | 2 |
| asr_cfo | sonnet | endpoint | 0 | 32 | 0 | 0 | 0 | 0 |
| asr_cfo | sonnet | handoff | 0 | 138 | 8 | 7 | 7 | 0 |
| asr_dpo | haiku | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| asr_dpo | haiku | handoff | 0 | 102 | 1 | 0 | 5 | 0 |
| asr_dpo | sonnet | endpoint | 0 | 17 | 0 | 0 | 0 | 0 |
| asr_dpo | sonnet | handoff | 0 | 97 | 0 | 0 | 6 | 0 |
| asr_interpreter | haiku | endpoint | 0 | 32 | 0 | 0 | 3 | 1 |
| asr_interpreter | haiku | handoff | 0 | 148 | 2 | 1 | 26 | 3 |
| asr_interpreter | sonnet | endpoint | 0 | 34 | 0 | 0 | 0 | 0 |
| asr_interpreter | sonnet | handoff | 4 | 152 | 6 | 1 | 6 | 1 |
| asr_signer | haiku | endpoint | 0 | 16 | 0 | 0 | 2 | 0 |
| asr_signer | haiku | handoff | 0 | 84 | 8 | 0 | 16 | 0 |
| asr_signer | sonnet | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| asr_signer | sonnet | handoff | 0 | 95 | 7 | 0 | 6 | 0 |
| homophone_children | haiku | endpoint | 0 | 0 | 0 | 0 | 0 | 18 |
| homophone_children | haiku | handoff | 0 | 1 | 0 | 0 | 13 | 76 |
| homophone_children | sonnet | endpoint | 0 | 3 | 0 | 0 | 0 | 15 |
| homophone_children | sonnet | handoff | 2 | 19 | 0 | 0 | 1 | 68 |
| homophone_delegates | haiku | endpoint | 0 | 0 | 0 | 0 | 16 | 2 |
| homophone_delegates | haiku | handoff | 2 | 41 | 1 | 0 | 41 | 5 |
| homophone_delegates | sonnet | endpoint | 0 | 0 | 0 | 14 | 4 | 0 |
| homophone_delegates | sonnet | handoff | 0 | 43 | 13 | 26 | 8 | 0 |
| homophone_guests | haiku | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| homophone_guests | haiku | handoff | 0 | 66 | 17 | 0 | 7 | 0 |
| homophone_guests | sonnet | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| homophone_guests | sonnet | handoff | 4 | 66 | 18 | 0 | 2 | 0 |
| homophone_period | haiku | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| homophone_period | haiku | handoff | 1 | 52 | 54 | 0 | 1 | 0 |
| homophone_period | sonnet | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| homophone_period | sonnet | handoff | 16 | 57 | 31 | 0 | 4 | 0 |
| homophone_two | haiku | endpoint | 0 | 0 | 0 | 17 | 1 | 0 |
| homophone_two | haiku | handoff | 0 | 0 | 0 | 96 | 6 | 6 |
| homophone_two | sonnet | endpoint | 0 | 4 | 0 | 14 | 0 | 0 |
| homophone_two | sonnet | handoff | 31 | 17 | 0 | 60 | 0 | 0 |
| homophone_warn | haiku | endpoint | 0 | 17 | 0 | 0 | 1 | 0 |
| homophone_warn | haiku | handoff | 2 | 98 | 3 | 0 | 5 | 0 |
| homophone_warn | sonnet | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| homophone_warn | sonnet | handoff | 1 | 99 | 4 | 0 | 4 | 0 |
| punct_alcohol | haiku | endpoint | 0 | 0 | 0 | 16 | 0 | 2 |
| punct_alcohol | haiku | handoff | 0 | 3 | 0 | 76 | 3 | 8 |
| punct_alcohol | sonnet | endpoint | 0 | 1 | 0 | 12 | 0 | 4 |
| punct_alcohol | sonnet | handoff | 0 | 4 | 0 | 67 | 2 | 12 |
| punct_cards | haiku | endpoint | 0 | 0 | 0 | 13 | 0 | 5 |
| punct_cards | haiku | handoff | 0 | 6 | 0 | 54 | 8 | 22 |
| punct_cards | sonnet | endpoint | 0 | 0 | 0 | 17 | 0 | 0 |
| punct_cards | sonnet | handoff | 0 | 0 | 0 | 79 | 1 | 5 |
| punct_channel | haiku | endpoint | 0 | 7 | 0 | 1 | 0 | 10 |
| punct_channel | haiku | handoff | 0 | 60 | 0 | 4 | 5 | 39 |
| punct_channel | sonnet | endpoint | 0 | 7 | 0 | 0 | 0 | 11 |
| punct_channel | sonnet | handoff | 1 | 60 | 0 | 0 | 0 | 47 |
| punct_record | haiku | endpoint | 0 | 0 | 0 | 15 | 1 | 2 |
| punct_record | haiku | handoff | 0 | 7 | 0 | 60 | 7 | 16 |
| punct_record | sonnet | endpoint | 0 | 0 | 0 | 18 | 0 | 0 |
| punct_record | sonnet | handoff | 0 | 5 | 0 | 80 | 3 | 2 |
| punct_trial | haiku | endpoint | 0 | 1 | 0 | 17 | 0 | 0 |
| punct_trial | haiku | handoff | 0 | 5 | 0 | 96 | 7 | 0 |
| punct_trial | sonnet | endpoint | 0 | 2 | 0 | 16 | 0 | 0 |
| punct_trial | sonnet | handoff | 7 | 8 | 0 | 88 | 5 | 0 |
| punct_warn | haiku | endpoint | 0 | 2 | 0 | 15 | 0 | 1 |
| punct_warn | haiku | handoff | 0 | 13 | 0 | 83 | 7 | 5 |
| punct_warn | sonnet | endpoint | 0 | 1 | 0 | 14 | 0 | 3 |
| punct_warn | sonnet | handoff | 0 | 6 | 0 | 89 | 4 | 9 |

## Endpoint by model and format

| scenario | model | handoff_format | runs | mean_score | all_passed | errors | checks_passed | checks | pass_rate |
|---|---|---|---|---|---|---|---|---|---|
| event_2 | haiku | forward | 24 | 0.759 | 10 | 8 | 346 | 456 | 0.759 |
| event_2 | haiku | free | 24 | 0.732 | 2 | 11 | 334 | 456 | 0.732 |
| event_2 | haiku | structured | 24 | 0.904 | 7 | 7 | 412 | 456 | 0.904 |
| event_2 | sonnet | forward | 22 | 0.962 | 11 | 4 | 402 | 418 | 0.962 |
| event_2 | sonnet | free | 23 | 0.938 | 7 | 3 | 410 | 437 | 0.938 |
| event_2 | sonnet | structured | 22 | 0.955 | 10 | 4 | 399 | 418 | 0.955 |
| event_3 | haiku | forward | 24 | 0.950 | 9 | 20 | 433 | 456 | 0.950 |
| event_3 | haiku | free | 24 | 0.836 | 2 | 24 | 381 | 456 | 0.836 |
| event_3 | haiku | structured | 24 | 0.914 | 4 | 24 | 417 | 456 | 0.914 |
| event_3 | sonnet | forward | 24 | 0.958 | 10 | 16 | 437 | 456 | 0.958 |
| event_3 | sonnet | free | 24 | 0.961 | 10 | 13 | 438 | 456 | 0.961 |
| event_3 | sonnet | structured | 24 | 0.961 | 12 | 18 | 438 | 456 | 0.961 |
| event_pilot | haiku | forward | 24 | 0.971 | 11 | 19 | 466 | 480 | 0.971 |
| event_pilot | haiku | free | 24 | 0.823 | 4 | 16 | 395 | 480 | 0.823 |
| event_pilot | haiku | structured | 24 | 0.915 | 6 | 16 | 439 | 480 | 0.915 |
| event_pilot | sonnet | forward | 20 | 0.963 | 6 | 3 | 385 | 400 | 0.963 |
| event_pilot | sonnet | free | 23 | 0.961 | 11 | 5 | 442 | 460 | 0.961 |
| event_pilot | sonnet | structured | 24 | 0.950 | 10 | 4 | 456 | 480 | 0.950 |
| software_2 | haiku | forward | 24 | 0.733 | 10 | 0 | 264 | 360 | 0.733 |
| software_2 | haiku | free | 24 | 0.750 | 11 | 0 | 270 | 360 | 0.750 |
| software_2 | haiku | structured | 24 | 0.639 | 10 | 0 | 230 | 360 | 0.639 |
| software_2 | sonnet | forward | 24 | 0.950 | 12 | 0 | 342 | 360 | 0.950 |
| software_2 | sonnet | free | 24 | 0.950 | 12 | 0 | 342 | 360 | 0.950 |
| software_2 | sonnet | structured | 24 | 0.867 | 10 | 0 | 312 | 360 | 0.867 |
| software_3 | haiku | forward | 24 | 0.764 | 9 | 0 | 275 | 360 | 0.764 |
| software_3 | haiku | free | 24 | 0.817 | 9 | 0 | 294 | 360 | 0.817 |
| software_3 | haiku | structured | 24 | 0.800 | 8 | 0 | 288 | 360 | 0.800 |
| software_3 | sonnet | forward | 24 | 0.942 | 7 | 0 | 339 | 360 | 0.942 |
| software_3 | sonnet | free | 24 | 0.900 | 7 | 0 | 324 | 360 | 0.900 |
| software_3 | sonnet | structured | 23 | 0.910 | 2 | 0 | 314 | 345 | 0.910 |
| software_pilot | haiku | forward | 24 | 0.639 | 8 | 0 | 276 | 432 | 0.639 |
| software_pilot | haiku | free | 24 | 0.586 | 5 | 0 | 253 | 432 | 0.586 |
| software_pilot | haiku | structured | 24 | 0.731 | 10 | 0 | 316 | 432 | 0.731 |
| software_pilot | sonnet | forward | 24 | 0.833 | 11 | 0 | 360 | 432 | 0.833 |
| software_pilot | sonnet | free | 24 | 0.819 | 12 | 0 | 354 | 432 | 0.819 |
| software_pilot | sonnet | structured | 24 | 0.900 | 12 | 0 | 389 | 432 | 0.900 |

## Endpoint by model

| scenario | model | runs | mean_score | all_passed | errors | checks_passed | checks | pass_rate |
|---|---|---|---|---|---|---|---|---|
| event_2 | haiku | 72 | 0.798 | 19 | 26 | 1092 | 1368 | 0.798 |
| event_2 | sonnet | 67 | 0.951 | 28 | 11 | 1211 | 1273 | 0.951 |
| event_3 | haiku | 72 | 0.900 | 15 | 68 | 1231 | 1368 | 0.900 |
| event_3 | sonnet | 72 | 0.960 | 32 | 47 | 1313 | 1368 | 0.960 |
| event_pilot | haiku | 72 | 0.903 | 21 | 51 | 1300 | 1440 | 0.903 |
| event_pilot | sonnet | 67 | 0.957 | 27 | 12 | 1283 | 1340 | 0.957 |
| software_2 | haiku | 72 | 0.707 | 31 | 0 | 764 | 1080 | 0.707 |
| software_2 | sonnet | 72 | 0.922 | 34 | 0 | 996 | 1080 | 0.922 |
| software_3 | haiku | 72 | 0.794 | 26 | 0 | 857 | 1080 | 0.794 |
| software_3 | sonnet | 71 | 0.917 | 16 | 0 | 977 | 1065 | 0.917 |
| software_pilot | haiku | 72 | 0.652 | 23 | 0 | 845 | 1296 | 0.652 |
| software_pilot | sonnet | 72 | 0.851 | 35 | 0 | 1103 | 1296 | 0.851 |

## Endpoint by topology and noise

| scenario | topology | noise | runs | mean_score | all_passed | errors | checks_passed | checks | pass_rate |
|---|---|---|---|---|---|---|---|---|---|
| event_2 | hier_chain | asr_interpreter | 17 | 0.777 | 0 | 4 | 251 | 323 | 0.777 |
| event_2 | hier_chain | clean | 16 | 0.931 | 13 | 2 | 283 | 304 | 0.931 |
| event_2 | hier_chain | homophone_children | 18 | 0.886 | 0 | 11 | 303 | 342 | 0.886 |
| event_2 | hier_chain | punct_cards | 18 | 0.886 | 15 | 2 | 303 | 342 | 0.886 |
| event_2 | hub_relay | asr_interpreter | 18 | 0.760 | 0 | 5 | 260 | 342 | 0.760 |
| event_2 | hub_relay | clean | 17 | 0.975 | 11 | 2 | 315 | 323 | 0.975 |
| event_2 | hub_relay | homophone_children | 18 | 0.871 | 0 | 7 | 298 | 342 | 0.871 |
| event_2 | hub_relay | punct_cards | 17 | 0.898 | 8 | 4 | 290 | 323 | 0.898 |
| event_3 | hier_chain | asr_av | 18 | 0.915 | 0 | 16 | 313 | 342 | 0.915 |
| event_3 | hier_chain | clean | 18 | 0.977 | 12 | 16 | 334 | 342 | 0.977 |
| event_3 | hier_chain | homophone_delegates | 18 | 0.930 | 3 | 16 | 318 | 342 | 0.930 |
| event_3 | hier_chain | punct_record | 18 | 0.965 | 7 | 15 | 330 | 342 | 0.965 |
| event_3 | hub_relay | asr_av | 18 | 0.874 | 0 | 12 | 299 | 342 | 0.874 |
| event_3 | hub_relay | clean | 18 | 0.918 | 9 | 13 | 314 | 342 | 0.918 |
| event_3 | hub_relay | homophone_delegates | 18 | 0.927 | 6 | 15 | 317 | 342 | 0.927 |
| event_3 | hub_relay | punct_record | 18 | 0.933 | 10 | 12 | 319 | 342 | 0.933 |
| event_pilot | hier_chain | asr_cfo | 17 | 0.929 | 0 | 7 | 316 | 340 | 0.929 |
| event_pilot | hier_chain | clean | 17 | 0.982 | 14 | 6 | 334 | 340 | 0.982 |
| event_pilot | hier_chain | homophone_guests | 18 | 0.889 | 0 | 7 | 320 | 360 | 0.889 |
| event_pilot | hier_chain | punct_alcohol | 18 | 0.992 | 15 | 9 | 357 | 360 | 0.992 |
| event_pilot | hub_relay | asr_cfo | 17 | 0.909 | 0 | 5 | 309 | 340 | 0.909 |
| event_pilot | hub_relay | clean | 17 | 0.906 | 12 | 9 | 308 | 340 | 0.906 |
| event_pilot | hub_relay | homophone_guests | 18 | 0.903 | 0 | 9 | 325 | 360 | 0.903 |
| event_pilot | hub_relay | punct_alcohol | 17 | 0.924 | 7 | 11 | 314 | 340 | 0.924 |
| software_2 | hier_chain | asr_approver | 18 | 0.778 | 0 | 0 | 210 | 270 | 0.778 |
| software_2 | hier_chain | clean | 18 | 0.889 | 16 | 0 | 240 | 270 | 0.889 |
| software_2 | hier_chain | homophone_period | 18 | 0.522 | 0 | 0 | 141 | 270 | 0.522 |
| software_2 | hier_chain | punct_trial | 18 | 0.778 | 14 | 0 | 210 | 270 | 0.778 |
| software_2 | hub_relay | asr_approver | 18 | 0.933 | 0 | 0 | 252 | 270 | 0.933 |
| software_2 | hub_relay | clean | 18 | 1.000 | 18 | 0 | 270 | 270 | 1.000 |
| software_2 | hub_relay | homophone_period | 18 | 0.674 | 0 | 0 | 182 | 270 | 0.674 |
| software_2 | hub_relay | punct_trial | 18 | 0.944 | 17 | 0 | 255 | 270 | 0.944 |
| software_3 | hier_chain | asr_dpo | 18 | 0.752 | 0 | 0 | 203 | 270 | 0.752 |
| software_3 | hier_chain | clean | 18 | 0.922 | 11 | 0 | 249 | 270 | 0.922 |
| software_3 | hier_chain | homophone_warn | 18 | 0.763 | 0 | 0 | 206 | 270 | 0.763 |
| software_3 | hier_chain | punct_warn | 18 | 0.756 | 9 | 0 | 204 | 270 | 0.756 |
| software_3 | hub_relay | asr_dpo | 17 | 0.871 | 0 | 0 | 222 | 255 | 0.871 |
| software_3 | hub_relay | clean | 18 | 0.878 | 10 | 0 | 237 | 270 | 0.878 |
| software_3 | hub_relay | homophone_warn | 18 | 0.922 | 0 | 0 | 249 | 270 | 0.922 |
| software_3 | hub_relay | punct_warn | 18 | 0.978 | 12 | 0 | 264 | 270 | 0.978 |
| software_pilot | hier_chain | asr_signer | 18 | 0.682 | 0 | 0 | 221 | 324 | 0.682 |
| software_pilot | hier_chain | clean | 18 | 0.722 | 13 | 0 | 234 | 324 | 0.722 |
| software_pilot | hier_chain | homophone_two | 18 | 0.769 | 12 | 0 | 249 | 324 | 0.769 |
| software_pilot | hier_chain | punct_channel | 18 | 0.330 | 1 | 0 | 107 | 324 | 0.330 |
| software_pilot | hub_relay | asr_signer | 18 | 0.944 | 0 | 0 | 306 | 324 | 0.944 |
| software_pilot | hub_relay | clean | 18 | 0.935 | 15 | 0 | 303 | 324 | 0.935 |
| software_pilot | hub_relay | homophone_two | 18 | 0.938 | 16 | 0 | 304 | 324 | 0.938 |
| software_pilot | hub_relay | punct_channel | 18 | 0.691 | 1 | 0 | 224 | 324 | 0.691 |

Endpoint rows above are text labels of code/JSON artifacts; the functional checks below are the endpoint measure (see the text-vs-check table).

## Endpoint artifact: text label vs functional check, per fact (note view)

| fact_id | text_label | n | check_passed |
|---|---|---|---|
| c_av_contact | distorted | 54 | 18 |
| c_av_contact | preserved | 90 | 89 |
| c_budget | preserved | 144 | 143 |
| c_chair | distorted | 25 | 25 |
| c_chair | lost | 4 | 0 |
| c_chair | preserved | 115 | 115 |
| c_cond_overflow | distorted | 142 | 141 |
| c_cond_overflow | lost | 2 | 0 |
| c_cond_strike | distorted | 4 | 0 |
| c_cond_strike | lost | 1 | 0 |
| c_cond_strike | preserved | 139 | 138 |
| c_date | preserved | 144 | 143 |
| c_delegates | distorted | 2 | 0 |
| c_delegates | lost | 21 | 0 |
| c_delegates | preserved | 121 | 120 |
| c_keynote_speaker | lost | 8 | 0 |
| c_keynote_speaker | preserved | 136 | 136 |
| c_keynote_time | lost | 3 | 0 |
| c_keynote_time | preserved | 141 | 140 |
| c_low_lapel | distorted | 1 | 1 |
| c_low_lapel | preserved | 143 | 139 |
| c_low_ratio | distorted | 1 | 0 |
| c_low_ratio | preserved | 143 | 129 |
| c_lunch | distorted | 144 | 143 |
| c_no_coffee | distorted | 83 | 70 |
| c_no_coffee | preserved | 61 | 5 |
| c_no_flash | distorted | 112 | 112 |
| c_no_flash | inverted | 2 | 0 |
| c_no_flash | preserved | 30 | 29 |
| c_no_record | distorted | 5 | 5 |
| c_no_record | lost | 11 | 11 |
| c_no_record | preserved | 128 | 127 |
| c_posters | lost | 3 | 0 |
| c_posters | preserved | 141 | 140 |
| c_priority_caption | distorted | 3 | 3 |
| c_priority_caption | lost | 29 | 29 |
| c_priority_caption | preserved | 112 | 111 |
| c_priority_questions | distorted | 25 | 25 |
| c_priority_questions | inverted | 4 | 0 |
| c_priority_questions | lost | 1 | 1 |
| c_priority_questions | preserved | 114 | 113 |
| c_venue | preserved | 144 | 143 |
| e_budget | preserved | 139 | 137 |
| e_ceo | distorted | 1 | 1 |
| e_ceo | lost | 9 | 0 |
| e_ceo | preserved | 129 | 124 |
| e_coach_time | preserved | 139 | 134 |
| e_cond_coach | distorted | 86 | 73 |
| e_cond_coach | lost | 1 | 0 |
| e_cond_coach | preserved | 52 | 51 |
| e_cond_rain | distorted | 50 | 45 |
| e_cond_rain | preserved | 89 | 88 |
| e_date | preserved | 139 | 137 |
| e_diet | preserved | 139 | 137 |
| e_dinner | preserved | 139 | 135 |
| e_guests | distorted | 36 | 0 |
| e_guests | preserved | 103 | 102 |
| e_low_lefty | distorted | 12 | 9 |
| e_low_lefty | lost | 7 | 0 |
| e_low_lefty | preserved | 120 | 116 |
| e_low_step_free | distorted | 40 | 40 |
| e_low_step_free | preserved | 99 | 97 |
| e_no_alcohol | distorted | 24 | 22 |
| e_no_alcohol | preserved | 115 | 115 |
| e_no_coachline | preserved | 139 | 137 |
| e_no_shellfish | distorted | 3 | 2 |
| e_no_shellfish | preserved | 136 | 123 |
| e_priority_band | distorted | 15 | 15 |
| e_priority_band | preserved | 124 | 122 |
| e_priority_keynote | distorted | 1 | 1 |
| e_priority_keynote | preserved | 138 | 136 |
| e_reception | preserved | 139 | 137 |
| e_speaker | lost | 16 | 0 |
| e_speaker | preserved | 123 | 116 |
| e_venue | preserved | 139 | 137 |
| e_vip_cfo | distorted | 33 | 0 |
| e_vip_cfo | lost | 10 | 0 |
| e_vip_cfo | preserved | 96 | 94 |
| f_approver | distorted | 36 | 0 |
| f_approver | lost | 2 | 0 |
| f_approver | preserved | 106 | 88 |
| f_approver_big | distorted | 1 | 0 |
| f_approver_big | lost | 2 | 0 |
| f_approver_big | preserved | 141 | 121 |
| f_batch | lost | 1 | 0 |
| f_batch | preserved | 142 | 129 |
| f_closed | distorted | 4 | 3 |
| f_closed | lost | 110 | 104 |
| f_closed | preserved | 29 | 23 |
| f_cond_big | distorted | 3 | 0 |
| f_cond_big | preserved | 141 | 121 |
| f_cond_channel | distorted | 33 | 19 |
| f_cond_channel | inverted | 22 | 0 |
| f_cond_channel | lost | 1 | 0 |
| f_cond_channel | preserved | 88 | 75 |
| f_cond_downgrade | distorted | 21 | 17 |
| f_cond_downgrade | preserved | 123 | 111 |
| f_cond_invoice | lost | 1 | 0 |
| f_cond_invoice | preserved | 142 | 129 |
| f_cond_late | distorted | 89 | 73 |
| f_cond_late | lost | 3 | 0 |
| f_cond_late | preserved | 52 | 36 |
| f_cond_pl | lost | 4 | 0 |
| f_cond_pl | preserved | 140 | 111 |
| f_cond_vat | distorted | 12 | 9 |
| f_cond_vat | inverted | 1 | 0 |
| f_cond_vat | preserved | 131 | 112 |
| f_cond_warn | distorted | 5 | 4 |
| f_cond_warn | inverted | 1 | 0 |
| f_cond_warn | lost | 1 | 0 |
| f_cond_warn | preserved | 136 | 126 |
| f_desc_len | lost | 1 | 1 |
| f_desc_len | preserved | 143 | 120 |
| f_dpo | distorted | 35 | 0 |
| f_dpo | lost | 4 | 0 |
| f_dpo | preserved | 104 | 96 |
| f_entry | lost | 3 | 0 |
| f_entry | preserved | 428 | 361 |
| f_first | lost | 4 | 1 |
| f_first | preserved | 140 | 109 |
| f_inactive | lost | 1 | 0 |
| f_inactive | preserved | 142 | 96 |
| f_low_int | lost | 1 | 0 |
| f_low_int | preserved | 143 | 129 |
| f_low_iso | preserved | 143 | 129 |
| f_low_order | lost | 1 | 0 |
| f_low_order | preserved | 143 | 121 |
| f_low_sorted | distorted | 3 | 1 |
| f_low_sorted | lost | 4 | 0 |
| f_low_sorted | preserved | 280 | 239 |
| f_low_tz | lost | 4 | 0 |
| f_low_tz | preserved | 140 | 108 |
| f_min | distorted | 15 | 14 |
| f_min | lost | 63 | 60 |
| f_min | preserved | 66 | 56 |
| f_no_both | lost | 2 | 0 |
| f_no_both | preserved | 142 | 118 |
| f_no_cancelled | lost | 1 | 0 |
| f_no_cancelled | preserved | 143 | 111 |
| f_no_email | inverted | 40 | 0 |
| f_no_email | lost | 1 | 0 |
| f_no_email | preserved | 102 | 90 |
| f_no_email_log | distorted | 2 | 2 |
| f_no_email_log | inverted | 2 | 1 |
| f_no_email_log | lost | 1 | 0 |
| f_no_email_log | preserved | 139 | 115 |
| f_no_hold | lost | 1 | 0 |
| f_no_hold | preserved | 142 | 129 |
| f_no_past | lost | 3 | 0 |
| f_no_past | preserved | 141 | 109 |
| f_no_round_us | distorted | 1 | 0 |
| f_no_round_us | inverted | 1 | 1 |
| f_no_round_us | preserved | 142 | 97 |
| f_no_staff | distorted | 1 | 0 |
| f_no_staff | lost | 1 | 0 |
| f_no_staff | preserved | 141 | 129 |
| f_no_trial | preserved | 144 | 121 |
| f_no_vat_credit | inverted | 2 | 0 |
| f_no_vat_credit | preserved | 142 | 121 |
| f_optout_field | lost | 2 | 0 |
| f_optout_field | preserved | 142 | 94 |
| f_period | distorted | 36 | 1 |
| f_period | lost | 43 | 42 |
| f_period | preserved | 65 | 55 |
| f_priority_closed | distorted | 1 | 1 |
| f_priority_closed | lost | 1 | 0 |
| f_priority_closed | preserved | 141 | 129 |
| f_priority_date | lost | 2 | 0 |
| f_priority_date | preserved | 142 | 121 |
| f_priority_time | distorted | 2 | 0 |
| f_priority_time | lost | 3 | 0 |
| f_priority_time | preserved | 139 | 108 |
| f_quiet | distorted | 115 | 91 |
| f_quiet | inverted | 3 | 1 |
| f_quiet | lost | 9 | 7 |
| f_quiet | preserved | 17 | 9 |
| f_seat_field | distorted | 2 | 0 |
| f_seat_field | preserved | 142 | 98 |
| f_second | lost | 3 | 1 |
| f_second | preserved | 141 | 109 |
| f_seen_field | lost | 1 | 0 |
| f_seen_field | preserved | 142 | 129 |
| f_signer | distorted | 34 | 0 |
| f_signer | lost | 4 | 0 |
| f_signer | preserved | 106 | 88 |
| f_signer_pl | lost | 3 | 0 |
| f_signer_pl | preserved | 141 | 111 |
| f_sms_len | lost | 2 | 0 |
| f_sms_len | preserved | 142 | 108 |
| f_vat_rate | lost | 99 | 86 |
| f_vat_rate | preserved | 45 | 35 |
| f_warn | distorted | 25 | 0 |
| f_warn | lost | 1 | 0 |
| f_warn | preserved | 117 | 96 |
| w_budget | preserved | 139 | 129 |
| w_ceremony | distorted | 3 | 3 |
| w_ceremony | lost | 1 | 0 |
| w_ceremony | preserved | 135 | 126 |
| w_cond_cards | distorted | 19 | 10 |
| w_cond_cards | inverted | 1 | 0 |
| w_cond_cards | preserved | 119 | 112 |
| w_cond_heat | distorted | 10 | 6 |
| w_cond_heat | lost | 1 | 0 |
| w_cond_heat | preserved | 128 | 121 |
| w_date | preserved | 139 | 106 |
| w_diet | distorted | 36 | 0 |
| w_diet | preserved | 103 | 95 |
| w_dinner | lost | 2 | 0 |
| w_dinner | preserved | 137 | 129 |
| w_grandmother | distorted | 1 | 1 |
| w_grandmother | lost | 6 | 0 |
| w_grandmother | preserved | 132 | 125 |
| w_guests | preserved | 139 | 129 |
| w_interpreter | distorted | 34 | 1 |
| w_interpreter | lost | 3 | 0 |
| w_interpreter | preserved | 102 | 97 |
| w_low_dog | distorted | 7 | 6 |
| w_low_dog | inverted | 1 | 1 |
| w_low_dog | preserved | 131 | 112 |
| w_low_hearing | distorted | 39 | 3 |
| w_low_hearing | lost | 4 | 0 |
| w_low_hearing | preserved | 96 | 92 |
| w_no_lumiere | distorted | 3 | 3 |
| w_no_lumiere | preserved | 136 | 126 |
| w_no_macarena | preserved | 139 | 129 |
| w_no_nuts | preserved | 139 | 128 |
| w_priority_interp | distorted | 28 | 23 |
| w_priority_interp | preserved | 111 | 104 |
| w_priority_late | distorted | 5 | 3 |
| w_priority_late | lost | 3 | 0 |
| w_priority_late | preserved | 131 | 126 |
| w_shuttle | lost | 1 | 0 |
| w_shuttle | preserved | 138 | 129 |
| w_venue | lost | 2 | 0 |
| w_venue | preserved | 137 | 128 |

## Plan consistency checks (untagged, not in the score)

| run_id | consistency |
|---|---|
| event_2-hub_relay-forward-homophone_children-haiku | budget_total_within_cap=False |
| event_2-hub_relay-forward-punct_cards-sonnet-s1 | budget_total_within_cap=True |
| event_2-hub_relay-free-homophone_children-haiku | budget_total_within_cap=True |
| event_2-hub_relay-free-punct_cards-haiku-s1 | budget_total_within_cap=True |
| event_2-hub_relay-structured-asr_interpreter-sonnet-s1 | budget_total_within_cap=True |
| event_2-hub_relay-structured-clean-haiku | budget_total_within_cap=True |
| event_2-hub_relay-structured-homophone_children-sonnet-s1 | budget_total_within_cap=True |
| event_3-hier_chain-structured-asr_av-sonnet | budget_total_within_cap=True |
| event_3-hier_chain-structured-asr_av-sonnet-s1 | budget_total_within_cap=True |
| event_3-hier_chain-structured-homophone_delegates-sonnet-s2 | budget_total_within_cap=True |
| event_3-hub_relay-free-asr_av-haiku | budget_total_within_cap=True |
| event_3-hub_relay-free-asr_av-haiku-s2 | budget_total_within_cap=True |
| event_3-hub_relay-free-homophone_delegates-haiku-s1 | budget_total_within_cap=True |
| event_3-hub_relay-free-homophone_delegates-haiku-s2 | budget_total_within_cap=True |
| event_3-hub_relay-free-punct_record-haiku-s2 | budget_total_within_cap=True |
| event_3-hub_relay-free-punct_record-sonnet-s2 | budget_total_within_cap=True |
| event_3-hub_relay-structured-asr_av-sonnet-s2 | budget_total_within_cap=True |
| event_3-hub_relay-structured-clean-sonnet | budget_total_within_cap=True |
| event_pilot-hier_chain-forward-punct_alcohol-sonnet-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-forward-asr_cfo-sonnet-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-forward-clean-sonnet-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-forward-homophone_guests-haiku | budget_total_within_cap=True |
| event_pilot-hub_relay-forward-homophone_guests-sonnet-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-free-asr_cfo-haiku | budget_total_within_cap=True |
| event_pilot-hub_relay-free-asr_cfo-haiku-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-free-asr_cfo-sonnet | budget_total_within_cap=True |
| event_pilot-hub_relay-free-clean-haiku | budget_total_within_cap=True |
| event_pilot-hub_relay-free-clean-haiku-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-free-clean-haiku-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-free-clean-sonnet-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-free-homophone_guests-haiku-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-free-homophone_guests-sonnet | budget_total_within_cap=True |
| event_pilot-hub_relay-free-homophone_guests-sonnet-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-free-punct_alcohol-haiku-s1 | budget_total_within_cap=False |
| event_pilot-hub_relay-structured-asr_cfo-haiku | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-clean-sonnet-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-homophone_guests-sonnet | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-homophone_guests-sonnet-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-homophone_guests-sonnet-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-punct_alcohol-sonnet | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-punct_alcohol-sonnet-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-punct_alcohol-sonnet-s2 | budget_total_within_cap=True |

## H7: fact label at the last downward hand-off vs its endpoint check (note view)

Forward runs, loss-insensitive facts, facts failed only through a dependency and the noise-affected facts of noisy runs are excluded (their wrong reading propagates by design: see the per-fact table).

| label_at_last_handoff | facts | endpoint_pass_rate |
|---|---|---|
| distorted | 204 | 0.863 |
| inverted | 5 | 0.800 |
| lost | 110 | 0.400 |
| preserved | 8589 | 0.953 |

Per fact (noise-affected facts of noisy runs kept and flagged):

| fact_id | label_at_last_handoff | noise_affected | facts | passed | endpoint_pass_rate |
|---|---|---|---|---|---|
| c_av_contact | distorted | True | 24 | 0 | 0.000 |
| c_av_contact | preserved | False | 72 | 71 | 0.986 |
| c_budget | preserved | False | 96 | 95 | 0.990 |
| c_chair | lost | False | 4 | 0 | 0.000 |
| c_chair | preserved | False | 92 | 92 | 1.000 |
| c_cond_overflow | distorted | False | 4 | 3 | 0.750 |
| c_cond_overflow | lost | False | 1 | 0 | 0.000 |
| c_cond_overflow | preserved | False | 91 | 90 | 0.989 |
| c_cond_strike | distorted | False | 7 | 5 | 0.714 |
| c_cond_strike | preserved | False | 89 | 85 | 0.955 |
| c_date | preserved | False | 96 | 95 | 0.990 |
| c_delegates | distorted | True | 14 | 0 | 0.000 |
| c_delegates | preserved | False | 72 | 70 | 0.972 |
| c_delegates | preserved | True | 10 | 10 | 1.000 |
| c_keynote_speaker | lost | False | 8 | 0 | 0.000 |
| c_keynote_speaker | preserved | False | 88 | 88 | 1.000 |
| c_keynote_time | lost | False | 2 | 0 | 0.000 |
| c_keynote_time | preserved | False | 94 | 92 | 0.979 |
| c_low_lapel | preserved | False | 92 | 92 | 1.000 |
| c_low_ratio | distorted | False | 3 | 3 | 1.000 |
| c_low_ratio | preserved | False | 93 | 79 | 0.849 |
| c_lunch | distorted | False | 1 | 1 | 1.000 |
| c_lunch | preserved | False | 95 | 94 | 0.989 |
| c_no_coffee | distorted | False | 4 | 2 | 0.500 |
| c_no_coffee | preserved | False | 92 | 46 | 0.500 |
| c_no_flash | distorted | False | 1 | 1 | 1.000 |
| c_no_flash | lost | False | 3 | 1 | 0.333 |
| c_no_flash | preserved | False | 92 | 91 | 0.989 |
| c_no_record | distorted | True | 3 | 3 | 1.000 |
| c_no_record | preserved | False | 72 | 71 | 0.986 |
| c_no_record | preserved | True | 21 | 21 | 1.000 |
| c_posters | lost | False | 3 | 0 | 0.000 |
| c_posters | preserved | False | 93 | 92 | 0.989 |
| c_priority_caption | distorted | False | 13 | 13 | 1.000 |
| c_priority_caption | preserved | False | 83 | 82 | 0.988 |
| c_priority_questions | distorted | False | 2 | 2 | 1.000 |
| c_priority_questions | lost | False | 12 | 7 | 0.583 |
| c_priority_questions | preserved | False | 82 | 82 | 1.000 |
| c_venue | preserved | False | 96 | 95 | 0.990 |
| e_budget | preserved | False | 95 | 93 | 0.979 |
| e_ceo | distorted | False | 1 | 1 | 1.000 |
| e_ceo | lost | False | 9 | 0 | 0.000 |
| e_ceo | preserved | False | 85 | 80 | 0.941 |
| e_coach_time | preserved | False | 95 | 91 | 0.958 |
| e_cond_coach | distorted | False | 12 | 4 | 0.333 |
| e_cond_coach | preserved | False | 83 | 77 | 0.928 |
| e_cond_rain | distorted | False | 7 | 3 | 0.429 |
| e_cond_rain | preserved | False | 88 | 86 | 0.977 |
| e_date | preserved | False | 95 | 93 | 0.979 |
| e_diet | preserved | False | 95 | 93 | 0.979 |
| e_dinner | preserved | False | 95 | 91 | 0.958 |
| e_guests | distorted | True | 24 | 0 | 0.000 |
| e_guests | preserved | False | 71 | 70 | 0.986 |
| e_low_lefty | distorted | False | 2 | 2 | 1.000 |
| e_low_lefty | preserved | False | 79 | 79 | 1.000 |
| e_low_step_free | distorted | False | 2 | 2 | 1.000 |
| e_low_step_free | distorted | True | 17 | 17 | 1.000 |
| e_low_step_free | preserved | False | 70 | 68 | 0.971 |
| e_low_step_free | preserved | True | 6 | 6 | 1.000 |
| e_no_alcohol | distorted | False | 8 | 7 | 0.875 |
| e_no_alcohol | distorted | True | 1 | 1 | 1.000 |
| e_no_alcohol | preserved | False | 63 | 62 | 0.984 |
| e_no_alcohol | preserved | True | 23 | 23 | 1.000 |
| e_no_coachline | distorted | False | 3 | 3 | 1.000 |
| e_no_coachline | preserved | False | 92 | 90 | 0.978 |
| e_no_shellfish | distorted | False | 1 | 1 | 1.000 |
| e_no_shellfish | preserved | False | 94 | 84 | 0.894 |
| e_priority_band | distorted | False | 8 | 8 | 1.000 |
| e_priority_band | preserved | False | 87 | 85 | 0.977 |
| e_priority_keynote | distorted | False | 3 | 3 | 1.000 |
| e_priority_keynote | lost | False | 2 | 2 | 1.000 |
| e_priority_keynote | preserved | False | 90 | 88 | 0.978 |
| e_reception | preserved | False | 95 | 93 | 0.979 |
| e_speaker | distorted | False | 1 | 1 | 1.000 |
| e_speaker | lost | False | 13 | 0 | 0.000 |
| e_speaker | preserved | False | 81 | 71 | 0.877 |
| e_venue | preserved | False | 95 | 93 | 0.979 |
| e_vip_cfo | distorted | True | 22 | 0 | 0.000 |
| e_vip_cfo | lost | False | 8 | 0 | 0.000 |
| e_vip_cfo | lost | True | 1 | 0 | 0.000 |
| e_vip_cfo | preserved | False | 64 | 61 | 0.953 |
| f_approver | distorted | True | 22 | 0 | 0.000 |
| f_approver | preserved | False | 57 | 57 | 1.000 |
| f_approver_big | preserved | False | 79 | 79 | 1.000 |
| f_batch | preserved | False | 86 | 86 | 1.000 |
| f_closed | distorted | False | 1 | 1 | 1.000 |
| f_closed | lost | False | 1 | 1 | 1.000 |
| f_closed | preserved | False | 84 | 84 | 1.000 |
| f_cond_big | preserved | False | 79 | 79 | 1.000 |
| f_cond_channel | distorted | False | 8 | 8 | 1.000 |
| f_cond_channel | distorted | True | 4 | 1 | 0.250 |
| f_cond_channel | inverted | True | 9 | 0 | 0.000 |
| f_cond_channel | preserved | False | 54 | 54 | 1.000 |
| f_cond_downgrade | distorted | False | 3 | 3 | 1.000 |
| f_cond_downgrade | preserved | False | 76 | 76 | 1.000 |
| f_cond_invoice | preserved | False | 86 | 86 | 1.000 |
| f_cond_late | distorted | False | 15 | 14 | 0.933 |
| f_cond_late | preserved | False | 60 | 60 | 1.000 |
| f_cond_pl | preserved | False | 75 | 75 | 1.000 |
| f_cond_vat | distorted | False | 7 | 7 | 1.000 |
| f_cond_vat | preserved | False | 72 | 72 | 1.000 |
| f_cond_warn | distorted | False | 2 | 2 | 1.000 |
| f_cond_warn | preserved | False | 63 | 63 | 1.000 |
| f_cond_warn | preserved | True | 21 | 21 | 1.000 |
| f_desc_len | preserved | False | 79 | 79 | 1.000 |
| f_dpo | distorted | True | 21 | 0 | 0.000 |
| f_dpo | lost | False | 1 | 0 | 0.000 |
| f_dpo | preserved | False | 64 | 63 | 0.984 |
| f_entry | preserved | False | 287 | 240 | 0.836 |
| f_first | lost | False | 2 | 1 | 0.500 |
| f_first | preserved | False | 73 | 73 | 1.000 |
| f_inactive | preserved | False | 86 | 64 | 0.744 |
| f_low_int | preserved | False | 79 | 79 | 1.000 |
| f_low_iso | preserved | False | 86 | 86 | 1.000 |
| f_low_sorted | preserved | False | 161 | 161 | 1.000 |
| f_low_tz | preserved | False | 75 | 73 | 0.973 |
| f_min | distorted | False | 4 | 4 | 1.000 |
| f_min | lost | False | 9 | 9 | 1.000 |
| f_min | preserved | False | 66 | 66 | 1.000 |
| f_no_cancelled | preserved | False | 75 | 75 | 1.000 |
| f_no_email | preserved | False | 86 | 56 | 0.651 |
| f_no_email_log | preserved | False | 75 | 74 | 0.987 |
| f_no_hold | distorted | False | 1 | 1 | 1.000 |
| f_no_hold | preserved | False | 85 | 85 | 1.000 |
| f_no_past | preserved | False | 75 | 74 | 0.987 |
| f_no_round_us | inverted | False | 5 | 4 | 0.800 |
| f_no_round_us | preserved | False | 74 | 61 | 0.824 |
| f_no_staff | distorted | False | 1 | 1 | 1.000 |
| f_no_staff | preserved | False | 85 | 85 | 1.000 |
| f_no_trial | preserved | False | 59 | 59 | 1.000 |
| f_no_trial | preserved | True | 20 | 20 | 1.000 |
| f_no_vat_credit | preserved | False | 79 | 79 | 1.000 |
| f_optout_field | preserved | False | 75 | 63 | 0.840 |
| f_period | distorted | True | 13 | 0 | 0.000 |
| f_period | preserved | False | 65 | 65 | 1.000 |
| f_period | preserved | True | 1 | 0 | 0.000 |
| f_priority_closed | distorted | False | 2 | 2 | 1.000 |
| f_priority_closed | preserved | False | 84 | 84 | 1.000 |
| f_priority_date | preserved | False | 79 | 79 | 1.000 |
| f_priority_time | preserved | False | 75 | 73 | 0.973 |
| f_quiet | distorted | False | 39 | 38 | 0.974 |
| f_quiet | preserved | False | 36 | 35 | 0.972 |
| f_seat_field | preserved | False | 79 | 65 | 0.823 |
| f_second | distorted | True | 1 | 0 | 0.000 |
| f_second | preserved | False | 54 | 54 | 1.000 |
| f_second | preserved | True | 20 | 20 | 1.000 |
| f_seen_field | preserved | False | 86 | 86 | 1.000 |
| f_signer | distorted | True | 20 | 0 | 0.000 |
| f_signer | preserved | False | 55 | 55 | 1.000 |
| f_signer_pl | preserved | False | 75 | 75 | 1.000 |
| f_sms_len | preserved | False | 75 | 73 | 0.973 |
| f_vat_rate | lost | False | 15 | 15 | 1.000 |
| f_vat_rate | preserved | False | 64 | 64 | 1.000 |
| f_warn | distorted | True | 16 | 0 | 0.000 |
| f_warn | preserved | False | 64 | 64 | 1.000 |
| f_warn | preserved | True | 6 | 0 | 0.000 |
| w_budget | preserved | False | 93 | 88 | 0.946 |
| w_ceremony | preserved | False | 93 | 88 | 0.946 |
| w_cond_cards | distorted | False | 6 | 3 | 0.500 |
| w_cond_cards | distorted | True | 3 | 1 | 0.333 |
| w_cond_cards | lost | False | 1 | 0 | 0.000 |
| w_cond_cards | lost | True | 1 | 0 | 0.000 |
| w_cond_cards | preserved | False | 63 | 60 | 0.952 |
| w_cond_cards | preserved | True | 19 | 17 | 0.895 |
| w_cond_heat | distorted | False | 3 | 1 | 0.333 |
| w_cond_heat | lost | False | 1 | 0 | 0.000 |
| w_cond_heat | preserved | False | 89 | 85 | 0.955 |
| w_date | preserved | False | 93 | 65 | 0.699 |
| w_diet | distorted | True | 22 | 0 | 0.000 |
| w_diet | lost | True | 2 | 0 | 0.000 |
| w_diet | preserved | False | 69 | 65 | 0.942 |
| w_dinner | preserved | False | 93 | 88 | 0.946 |
| w_grandmother | lost | False | 4 | 0 | 0.000 |
| w_grandmother | preserved | False | 89 | 85 | 0.955 |
| w_guests | preserved | False | 93 | 88 | 0.946 |
| w_interpreter | distorted | True | 22 | 0 | 0.000 |
| w_interpreter | lost | False | 1 | 0 | 0.000 |
| w_interpreter | lost | True | 2 | 0 | 0.000 |
| w_interpreter | preserved | False | 68 | 65 | 0.956 |
| w_low_dog | distorted | False | 1 | 1 | 1.000 |
| w_low_dog | preserved | False | 92 | 78 | 0.848 |
| w_low_hearing | distorted | False | 3 | 2 | 0.667 |
| w_low_hearing | preserved | False | 60 | 60 | 1.000 |
| w_no_lumiere | preserved | False | 93 | 88 | 0.946 |
| w_no_macarena | preserved | False | 93 | 88 | 0.946 |
| w_no_nuts | preserved | False | 93 | 88 | 0.946 |
| w_priority_interp | distorted | False | 23 | 21 | 0.913 |
| w_priority_interp | preserved | False | 70 | 67 | 0.957 |
| w_priority_late | distorted | False | 2 | 2 | 1.000 |
| w_priority_late | lost | False | 9 | 8 | 0.889 |
| w_priority_late | preserved | False | 82 | 78 | 0.951 |
| w_shuttle | preserved | False | 93 | 88 | 0.946 |
| w_venue | lost | False | 1 | 0 | 0.000 |
| w_venue | preserved | False | 92 | 87 | 0.946 |

## Hand-off output tokens (per message, from the stream; see runner_cc.turn_usage)

| model | direction | messages | median_output_tokens | total_output_tokens | estimated_share |
|---|---|---|---|---|---|
| haiku | down | 972 | 1680.000 | 2618130 | 0.889 |
| haiku | up | 1404 | 4051.500 | 8611573 | 0.308 |
| sonnet | down | 950 | 1235.000 | 1411550 | 0.892 |
| sonnet | up | 1371 | 2972 | 5353841 | 0.307 |

## Invented claims by distance (judge, note view)

| kind | distance | messages | invented | per_message |
|---|---|---|---|---|
| source | 1 | 853 | 215 | 0.252 |
| handoff | 2 | 853 | 2184 | 2.560 |
| handoff | 3 | 853 | 14486 | 16.982 |
| endpoint | 4 | 211 | 2304 | 10.919 |
| handoff | 4 | 853 | 15040 | 17.632 |
| endpoint | 5 | 642 | 8047 | 12.534 |
| handoff | 5 | 853 | 10491 | 12.299 |
| handoff | 6 | 853 | 10719 | 12.566 |
| handoff | 7 | 216 | 3131 | 14.495 |
| handoff | 8 | 216 | 3147 | 14.569 |
