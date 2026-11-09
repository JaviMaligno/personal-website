# agent-telephone — Claude Code pilot, scored

- 432 valid runs, 2052 messages, 43056 scored units (note view), 432 endpoint evaluations.
- Judge: claude-opus-5-5 via claude, passes ['note/0', 'full/0', 'note/1']; pass 0 vs 1 κ = 0.969 (n = 24423)

## Survival by distance (note view; source, downward non-forward hand-offs, endpoint)

| kind | distance | scored | survival | lost_rate | distorted_rate | inverted_rate | unscored |
|---|---|---|---|---|---|---|---|
| endpoint | 4 | 2304 | 0.831 | 0.099 | 0.069 | 0.001 | 0 |
| endpoint | 5 | 6768 | 0.718 | 0.215 | 0.057 | 0.009 | 0 |
| handoff | 2 | 6048 | 0.915 | 0.056 | 0.027 | 0.003 | 0 |
| handoff | 3 | 3024 | 0.905 | 0.063 | 0.029 | 0.003 | 0 |
| handoff | 4 | 4512 | 0.883 | 0.076 | 0.037 | 0.004 | 0 |
| source | 1 | 9072 | 0.960 | 0.000 | 0.032 | 0.008 | 0 |

## Survival by information distance (hand-offs, note view)

| kind | info_distance | scored | survival | lost_rate | distorted_rate | inverted_rate |
|---|---|---|---|---|---|---|
| handoff | 2 | 9072 | 0.910 | 0.058 | 0.028 | 0.003 |
| handoff | 3 | 3024 | 0.905 | 0.063 | 0.029 | 0.003 |
| handoff | 4 | 1488 | 0.844 | 0.102 | 0.048 | 0.005 |

## Hand-off survival by fact type (note view; downward, non-forward)

| fact_type | distance | scored | survival | lost_rate | distorted_rate | inverted_rate |
|---|---|---|---|---|---|---|
| conditional | 2 | 672 | 0.973 | 0.000 | 0.010 | 0.016 |
| conditional | 3 | 336 | 0.961 | 0.000 | 0.024 | 0.015 |
| conditional | 4 | 528 | 0.943 | 0.002 | 0.034 | 0.021 |
| low_salience | 2 | 720 | 0.971 | 0.007 | 0.022 | 0.000 |
| low_salience | 3 | 360 | 0.964 | 0.011 | 0.025 | 0.000 |
| low_salience | 4 | 576 | 0.960 | 0.016 | 0.024 | 0.000 |
| name | 2 | 1056 | 0.925 | 0.000 | 0.075 | 0.000 |
| name | 3 | 528 | 0.922 | 0.000 | 0.078 | 0.000 |
| name | 4 | 792 | 0.914 | 0.000 | 0.086 | 0.000 |
| negation | 2 | 912 | 0.986 | 0.001 | 0.004 | 0.009 |
| negation | 3 | 456 | 0.989 | 0.002 | 0.002 | 0.007 |
| negation | 4 | 696 | 0.987 | 0.003 | 0.000 | 0.010 |
| number | 2 | 1536 | 0.967 | 0.001 | 0.033 | 0.000 |
| number | 3 | 768 | 0.966 | 0.004 | 0.030 | 0.000 |
| number | 4 | 1056 | 0.940 | 0.006 | 0.054 | 0.000 |
| priority | 2 | 576 | 0.993 | 0.005 | 0.002 | 0.000 |
| priority | 3 | 288 | 0.972 | 0.024 | 0.003 | 0.000 |
| priority | 4 | 432 | 0.942 | 0.046 | 0.012 | 0.000 |
| rationale | 2 | 576 | 0.425 | 0.566 | 0.009 | 0.000 |
| rationale | 3 | 288 | 0.375 | 0.608 | 0.017 | 0.000 |
| rationale | 4 | 432 | 0.282 | 0.706 | 0.012 | 0.000 |

## Hand-off survival by model (note view; downward, non-forward)

| model | distance | scored | survival | lost_rate | distorted_rate | inverted_rate |
|---|---|---|---|---|---|---|
| gpt-6-luna | 2 | 6048 | 0.915 | 0.056 | 0.027 | 0.003 |
| gpt-6-luna | 3 | 3024 | 0.905 | 0.063 | 0.029 | 0.003 |
| gpt-6-luna | 4 | 4512 | 0.883 | 0.076 | 0.037 | 0.004 |

## Hand-off survival by format (note view; free vs structured)

| handoff_format | distance | scored | survival | lost_rate | distorted_rate | inverted_rate |
|---|---|---|---|---|---|---|
| free | 2 | 3024 | 0.907 | 0.061 | 0.030 | 0.002 |
| free | 3 | 1512 | 0.891 | 0.073 | 0.035 | 0.001 |
| free | 4 | 2256 | 0.863 | 0.090 | 0.043 | 0.003 |
| structured | 2 | 3024 | 0.922 | 0.050 | 0.023 | 0.005 |
| structured | 3 | 1512 | 0.920 | 0.053 | 0.023 | 0.004 |
| structured | 4 | 2256 | 0.902 | 0.062 | 0.031 | 0.005 |

## Upward hand-backs (note view)

| topology | distance | scored | survival | lost_rate | distorted_rate | inverted_rate |
|---|---|---|---|---|---|---|
| hub_relay | 3 | 4536 | 0.813 | 0.152 | 0.032 | 0.003 |

## Forward notes: contradiction of the attached original (note view)

| model | direction | distance | n | scored | contradicted | contradiction_rate | noise_reading | silent_rate |
|---|---|---|---|---|---|---|---|---|
| gpt-6-luna | down | 2 | 3024 | 3024 | 138 | 0.046 | 7 | 0.634 |
| gpt-6-luna | down | 3 | 1512 | 1512 | 44 | 0.029 | 10 | 0.354 |
| gpt-6-luna | down | 4 | 2256 | 2256 | 70 | 0.031 | 14 | 0.491 |
| gpt-6-luna | up | 3 | 1512 | 1512 | 42 | 0.028 | 11 | 0.333 |

## Noise propagation (asr variants, note view)

| noise_kind | kind | distance | flagged | freeze | amplify | repair | lost | drift |
|---|---|---|---|---|---|---|---|---|
| asr_name | endpoint | 4 | 0 | 45 | 0 | 0 | 0 | 0 |
| asr_name | endpoint | 5 | 0 | 96 | 0 | 0 | 3 | 0 |
| asr_name | handoff | 2 | 0 | 108 | 0 | 3 | 32 | 1 |
| asr_name | handoff | 3 | 0 | 125 | 0 | 2 | 17 | 0 |
| asr_name | handoff | 4 | 0 | 71 | 5 | 3 | 20 | 0 |
| homophone | endpoint | 4 | 0 | 9 | 0 | 7 | 4 | 7 |
| homophone | endpoint | 5 | 0 | 44 | 0 | 23 | 6 | 8 |
| homophone | handoff | 2 | 0 | 37 | 5 | 25 | 27 | 14 |
| homophone | handoff | 3 | 0 | 46 | 6 | 28 | 14 | 14 |
| homophone | handoff | 4 | 0 | 35 | 6 | 23 | 13 | 4 |
| punct | endpoint | 4 | 0 | 0 | 0 | 21 | 0 | 6 |
| punct | endpoint | 5 | 0 | 0 | 0 | 55 | 0 | 26 |
| punct | handoff | 2 | 0 | 6 | 0 | 71 | 16 | 15 |
| punct | handoff | 3 | 0 | 6 | 0 | 88 | 1 | 13 |
| punct | handoff | 4 | 0 | 4 | 0 | 58 | 5 | 14 |

By model (all distances):

| noise | model | kind | flagged | freeze | amplify | repair | lost | drift |
|---|---|---|---|---|---|---|---|---|
| asr_approver | gpt-6-luna | endpoint | 0 | 17 | 0 | 0 | 1 | 0 |
| asr_approver | gpt-6-luna | handoff | 0 | 37 | 3 | 0 | 14 | 0 |
| asr_av | gpt-6-luna | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| asr_av | gpt-6-luna | handoff | 0 | 35 | 0 | 0 | 10 | 0 |
| asr_cfo | gpt-6-luna | endpoint | 0 | 36 | 0 | 0 | 0 | 0 |
| asr_cfo | gpt-6-luna | handoff | 0 | 72 | 0 | 8 | 10 | 0 |
| asr_dpo | gpt-6-luna | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| asr_dpo | gpt-6-luna | handoff | 0 | 39 | 1 | 0 | 14 | 0 |
| asr_interpreter | gpt-6-luna | endpoint | 0 | 34 | 0 | 0 | 2 | 0 |
| asr_interpreter | gpt-6-luna | handoff | 0 | 84 | 0 | 0 | 5 | 1 |
| asr_signer | gpt-6-luna | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| asr_signer | gpt-6-luna | handoff | 0 | 37 | 1 | 0 | 16 | 0 |
| homophone_children | gpt-6-luna | endpoint | 0 | 0 | 0 | 2 | 1 | 15 |
| homophone_children | gpt-6-luna | handoff | 0 | 0 | 0 | 0 | 15 | 30 |
| homophone_delegates | gpt-6-luna | endpoint | 0 | 0 | 0 | 15 | 3 | 0 |
| homophone_delegates | gpt-6-luna | handoff | 0 | 3 | 0 | 32 | 10 | 0 |
| homophone_guests | gpt-6-luna | endpoint | 0 | 17 | 0 | 0 | 1 | 0 |
| homophone_guests | gpt-6-luna | handoff | 0 | 32 | 1 | 0 | 12 | 0 |
| homophone_period | gpt-6-luna | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| homophone_period | gpt-6-luna | handoff | 0 | 30 | 16 | 0 | 8 | 0 |
| homophone_two | gpt-6-luna | endpoint | 0 | 0 | 0 | 13 | 5 | 0 |
| homophone_two | gpt-6-luna | handoff | 0 | 4 | 0 | 44 | 4 | 2 |
| homophone_warn | gpt-6-luna | endpoint | 0 | 18 | 0 | 0 | 0 | 0 |
| homophone_warn | gpt-6-luna | handoff | 0 | 49 | 0 | 0 | 5 | 0 |
| punct_alcohol | gpt-6-luna | endpoint | 0 | 0 | 0 | 18 | 0 | 0 |
| punct_alcohol | gpt-6-luna | handoff | 0 | 0 | 0 | 42 | 2 | 1 |
| punct_cards | gpt-6-luna | endpoint | 0 | 0 | 0 | 8 | 0 | 10 |
| punct_cards | gpt-6-luna | handoff | 0 | 0 | 0 | 38 | 3 | 4 |
| punct_channel | gpt-6-luna | endpoint | 0 | 0 | 0 | 3 | 0 | 15 |
| punct_channel | gpt-6-luna | handoff | 0 | 16 | 0 | 5 | 3 | 30 |
| punct_record | gpt-6-luna | endpoint | 0 | 0 | 0 | 16 | 0 | 2 |
| punct_record | gpt-6-luna | handoff | 0 | 0 | 0 | 37 | 3 | 5 |
| punct_trial | gpt-6-luna | endpoint | 0 | 0 | 0 | 18 | 0 | 0 |
| punct_trial | gpt-6-luna | handoff | 0 | 0 | 0 | 47 | 7 | 0 |
| punct_warn | gpt-6-luna | endpoint | 0 | 0 | 0 | 13 | 0 | 5 |
| punct_warn | gpt-6-luna | handoff | 0 | 0 | 0 | 48 | 4 | 2 |

## Endpoint by model and format

| scenario | model | handoff_format | runs | mean_score | all_passed | errors | checks_passed | checks | pass_rate |
|---|---|---|---|---|---|---|---|---|---|
| event_2 | gpt-6-luna | forward | 24 | 0.871 | 2 | 3 | 397 | 456 | 0.871 |
| event_2 | gpt-6-luna | free | 24 | 0.864 | 2 | 3 | 394 | 456 | 0.864 |
| event_2 | gpt-6-luna | structured | 24 | 0.914 | 4 | 0 | 417 | 456 | 0.914 |
| event_3 | gpt-6-luna | forward | 24 | 0.967 | 13 | 8 | 441 | 456 | 0.967 |
| event_3 | gpt-6-luna | free | 24 | 0.936 | 14 | 12 | 427 | 456 | 0.936 |
| event_3 | gpt-6-luna | structured | 24 | 0.985 | 17 | 11 | 449 | 456 | 0.985 |
| event_pilot | gpt-6-luna | forward | 24 | 0.875 | 7 | 10 | 420 | 480 | 0.875 |
| event_pilot | gpt-6-luna | free | 24 | 0.900 | 5 | 12 | 432 | 480 | 0.900 |
| event_pilot | gpt-6-luna | structured | 24 | 0.892 | 3 | 7 | 428 | 480 | 0.892 |
| software_2 | gpt-6-luna | forward | 24 | 0.792 | 5 | 0 | 285 | 360 | 0.792 |
| software_2 | gpt-6-luna | free | 24 | 0.186 | 1 | 0 | 67 | 360 | 0.186 |
| software_2 | gpt-6-luna | structured | 24 | 0.944 | 11 | 0 | 340 | 360 | 0.944 |
| software_3 | gpt-6-luna | forward | 24 | 0.919 | 4 | 0 | 331 | 360 | 0.919 |
| software_3 | gpt-6-luna | free | 24 | 0.158 | 1 | 0 | 57 | 360 | 0.158 |
| software_3 | gpt-6-luna | structured | 24 | 0.578 | 1 | 0 | 208 | 360 | 0.578 |
| software_pilot | gpt-6-luna | forward | 24 | 0.868 | 6 | 0 | 375 | 432 | 0.868 |
| software_pilot | gpt-6-luna | free | 24 | 0.333 | 0 | 0 | 144 | 432 | 0.333 |
| software_pilot | gpt-6-luna | structured | 24 | 0.745 | 7 | 0 | 322 | 432 | 0.745 |

## Endpoint by model

| scenario | model | runs | mean_score | all_passed | errors | checks_passed | checks | pass_rate |
|---|---|---|---|---|---|---|---|---|
| event_2 | gpt-6-luna | 72 | 0.883 | 8 | 6 | 1208 | 1368 | 0.883 |
| event_3 | gpt-6-luna | 72 | 0.963 | 44 | 31 | 1317 | 1368 | 0.963 |
| event_pilot | gpt-6-luna | 72 | 0.889 | 15 | 29 | 1280 | 1440 | 0.889 |
| software_2 | gpt-6-luna | 72 | 0.641 | 17 | 0 | 692 | 1080 | 0.641 |
| software_3 | gpt-6-luna | 72 | 0.552 | 6 | 0 | 596 | 1080 | 0.552 |
| software_pilot | gpt-6-luna | 72 | 0.649 | 13 | 0 | 841 | 1296 | 0.649 |

## Endpoint by topology and noise

| scenario | topology | noise | runs | mean_score | all_passed | errors | checks_passed | checks | pass_rate |
|---|---|---|---|---|---|---|---|---|---|
| event_2 | hier_chain | asr_interpreter | 9 | 0.848 | 0 | 0 | 145 | 171 | 0.848 |
| event_2 | hier_chain | clean | 9 | 0.953 | 2 | 0 | 163 | 171 | 0.953 |
| event_2 | hier_chain | homophone_children | 9 | 0.784 | 0 | 1 | 134 | 171 | 0.784 |
| event_2 | hier_chain | punct_cards | 9 | 0.959 | 3 | 0 | 164 | 171 | 0.959 |
| event_2 | hub_relay | asr_interpreter | 9 | 0.754 | 0 | 1 | 129 | 171 | 0.754 |
| event_2 | hub_relay | clean | 9 | 0.936 | 1 | 1 | 160 | 171 | 0.936 |
| event_2 | hub_relay | homophone_children | 9 | 0.883 | 0 | 1 | 151 | 171 | 0.883 |
| event_2 | hub_relay | punct_cards | 9 | 0.947 | 2 | 2 | 162 | 171 | 0.947 |
| event_3 | hier_chain | asr_av | 9 | 0.936 | 0 | 3 | 160 | 171 | 0.936 |
| event_3 | hier_chain | clean | 9 | 0.988 | 7 | 5 | 169 | 171 | 0.988 |
| event_3 | hier_chain | homophone_delegates | 9 | 0.977 | 6 | 4 | 167 | 171 | 0.977 |
| event_3 | hier_chain | punct_record | 9 | 0.982 | 6 | 3 | 168 | 171 | 0.982 |
| event_3 | hub_relay | asr_av | 9 | 0.936 | 0 | 5 | 160 | 171 | 0.936 |
| event_3 | hub_relay | clean | 9 | 0.883 | 7 | 4 | 151 | 171 | 0.883 |
| event_3 | hub_relay | homophone_delegates | 9 | 1.000 | 9 | 4 | 171 | 171 | 1.000 |
| event_3 | hub_relay | punct_record | 9 | 1.000 | 9 | 3 | 171 | 171 | 1.000 |
| event_pilot | hier_chain | asr_cfo | 9 | 0.822 | 0 | 1 | 148 | 180 | 0.822 |
| event_pilot | hier_chain | clean | 9 | 0.850 | 4 | 3 | 153 | 180 | 0.850 |
| event_pilot | hier_chain | homophone_guests | 9 | 0.911 | 0 | 4 | 164 | 180 | 0.911 |
| event_pilot | hier_chain | punct_alcohol | 9 | 0.967 | 4 | 4 | 174 | 180 | 0.967 |
| event_pilot | hub_relay | asr_cfo | 9 | 0.928 | 0 | 5 | 167 | 180 | 0.928 |
| event_pilot | hub_relay | clean | 9 | 0.967 | 4 | 4 | 174 | 180 | 0.967 |
| event_pilot | hub_relay | homophone_guests | 9 | 0.911 | 0 | 3 | 164 | 180 | 0.911 |
| event_pilot | hub_relay | punct_alcohol | 9 | 0.756 | 3 | 5 | 136 | 180 | 0.756 |
| software_2 | hier_chain | asr_approver | 9 | 0.533 | 0 | 0 | 72 | 135 | 0.533 |
| software_2 | hier_chain | clean | 9 | 0.667 | 6 | 0 | 90 | 135 | 0.667 |
| software_2 | hier_chain | homophone_period | 9 | 0.563 | 0 | 0 | 76 | 135 | 0.563 |
| software_2 | hier_chain | punct_trial | 9 | 0.615 | 4 | 0 | 83 | 135 | 0.615 |
| software_2 | hub_relay | asr_approver | 9 | 0.726 | 0 | 0 | 98 | 135 | 0.726 |
| software_2 | hub_relay | clean | 9 | 0.793 | 3 | 0 | 107 | 135 | 0.793 |
| software_2 | hub_relay | homophone_period | 9 | 0.652 | 0 | 0 | 88 | 135 | 0.652 |
| software_2 | hub_relay | punct_trial | 9 | 0.578 | 4 | 0 | 78 | 135 | 0.578 |
| software_3 | hier_chain | asr_dpo | 9 | 0.600 | 0 | 0 | 81 | 135 | 0.600 |
| software_3 | hier_chain | clean | 9 | 0.593 | 2 | 0 | 80 | 135 | 0.593 |
| software_3 | hier_chain | homophone_warn | 9 | 0.415 | 0 | 0 | 56 | 135 | 0.415 |
| software_3 | hier_chain | punct_warn | 9 | 0.652 | 1 | 0 | 88 | 135 | 0.652 |
| software_3 | hub_relay | asr_dpo | 9 | 0.526 | 0 | 0 | 71 | 135 | 0.526 |
| software_3 | hub_relay | clean | 9 | 0.541 | 3 | 0 | 73 | 135 | 0.541 |
| software_3 | hub_relay | homophone_warn | 9 | 0.570 | 0 | 0 | 77 | 135 | 0.570 |
| software_3 | hub_relay | punct_warn | 9 | 0.519 | 0 | 0 | 70 | 135 | 0.519 |
| software_pilot | hier_chain | asr_signer | 9 | 0.512 | 0 | 0 | 83 | 162 | 0.512 |
| software_pilot | hier_chain | clean | 9 | 0.765 | 5 | 0 | 124 | 162 | 0.765 |
| software_pilot | hier_chain | homophone_two | 9 | 0.531 | 2 | 0 | 86 | 162 | 0.531 |
| software_pilot | hier_chain | punct_channel | 9 | 0.525 | 1 | 0 | 85 | 162 | 0.525 |
| software_pilot | hub_relay | asr_signer | 9 | 0.821 | 0 | 0 | 133 | 162 | 0.821 |
| software_pilot | hub_relay | clean | 9 | 0.728 | 3 | 0 | 118 | 162 | 0.728 |
| software_pilot | hub_relay | homophone_two | 9 | 0.642 | 2 | 0 | 104 | 162 | 0.642 |
| software_pilot | hub_relay | punct_channel | 9 | 0.667 | 0 | 0 | 108 | 162 | 0.667 |

Endpoint rows above are text labels of code/JSON artifacts; the functional checks below are the endpoint measure (see the text-vs-check table).

## Endpoint artifact: text label vs functional check, per fact (note view)

| fact_id | text_label | n | check_passed |
|---|---|---|---|
| c_av_contact | distorted | 18 | 0 |
| c_av_contact | preserved | 54 | 53 |
| c_budget | preserved | 72 | 71 |
| c_chair | distorted | 13 | 13 |
| c_chair | preserved | 59 | 58 |
| c_cond_overflow | preserved | 72 | 71 |
| c_cond_strike | distorted | 7 | 0 |
| c_cond_strike | preserved | 65 | 64 |
| c_date | preserved | 72 | 71 |
| c_delegates | lost | 3 | 0 |
| c_delegates | preserved | 69 | 68 |
| c_keynote_speaker | preserved | 72 | 71 |
| c_keynote_time | preserved | 72 | 71 |
| c_low_lapel | preserved | 72 | 71 |
| c_low_ratio | preserved | 72 | 70 |
| c_lunch | distorted | 72 | 71 |
| c_no_coffee | distorted | 36 | 35 |
| c_no_coffee | preserved | 36 | 36 |
| c_no_flash | preserved | 72 | 71 |
| c_no_record | distorted | 1 | 1 |
| c_no_record | inverted | 1 | 0 |
| c_no_record | preserved | 70 | 69 |
| c_posters | preserved | 72 | 71 |
| c_priority_caption | distorted | 2 | 2 |
| c_priority_caption | inverted | 1 | 0 |
| c_priority_caption | preserved | 69 | 68 |
| c_priority_questions | inverted | 1 | 0 |
| c_priority_questions | preserved | 71 | 70 |
| c_venue | preserved | 72 | 71 |
| e_budget | preserved | 72 | 68 |
| e_ceo | preserved | 72 | 68 |
| e_coach_time | preserved | 72 | 68 |
| e_cond_coach | distorted | 1 | 1 |
| e_cond_coach | preserved | 71 | 67 |
| e_cond_rain | distorted | 1 | 1 |
| e_cond_rain | preserved | 71 | 67 |
| e_date | preserved | 72 | 68 |
| e_diet | preserved | 72 | 68 |
| e_dinner | preserved | 72 | 66 |
| e_guests | distorted | 17 | 0 |
| e_guests | lost | 1 | 0 |
| e_guests | preserved | 54 | 50 |
| e_low_lefty | preserved | 72 | 68 |
| e_low_step_free | distorted | 5 | 5 |
| e_low_step_free | preserved | 67 | 63 |
| e_no_alcohol | preserved | 72 | 68 |
| e_no_coachline | lost | 4 | 3 |
| e_no_coachline | preserved | 68 | 65 |
| e_no_shellfish | distorted | 9 | 8 |
| e_no_shellfish | preserved | 63 | 29 |
| e_priority_band | preserved | 72 | 68 |
| e_priority_keynote | preserved | 72 | 68 |
| e_reception | distorted | 1 | 0 |
| e_reception | preserved | 71 | 66 |
| e_speaker | lost | 8 | 0 |
| e_speaker | preserved | 64 | 58 |
| e_venue | preserved | 72 | 68 |
| e_vip_cfo | distorted | 18 | 0 |
| e_vip_cfo | preserved | 54 | 51 |
| f_approver | distorted | 17 | 0 |
| f_approver | lost | 1 | 0 |
| f_approver | preserved | 54 | 36 |
| f_approver_big | distorted | 12 | 0 |
| f_approver_big | lost | 1 | 0 |
| f_approver_big | preserved | 59 | 41 |
| f_batch | preserved | 72 | 50 |
| f_closed | distorted | 1 | 0 |
| f_closed | lost | 68 | 39 |
| f_closed | preserved | 3 | 2 |
| f_cond_big | distorted | 12 | 0 |
| f_cond_big | lost | 1 | 0 |
| f_cond_big | preserved | 59 | 41 |
| f_cond_channel | distorted | 11 | 1 |
| f_cond_channel | inverted | 6 | 0 |
| f_cond_channel | lost | 1 | 0 |
| f_cond_channel | preserved | 54 | 39 |
| f_cond_downgrade | distorted | 7 | 6 |
| f_cond_downgrade | preserved | 65 | 47 |
| f_cond_invoice | distorted | 4 | 0 |
| f_cond_invoice | preserved | 68 | 42 |
| f_cond_late | lost | 2 | 0 |
| f_cond_late | preserved | 70 | 48 |
| f_cond_pl | lost | 2 | 0 |
| f_cond_pl | preserved | 70 | 48 |
| f_cond_vat | distorted | 3 | 0 |
| f_cond_vat | lost | 1 | 0 |
| f_cond_vat | preserved | 68 | 50 |
| f_cond_warn | distorted | 16 | 0 |
| f_cond_warn | lost | 1 | 0 |
| f_cond_warn | preserved | 55 | 41 |
| f_desc_len | lost | 1 | 0 |
| f_desc_len | preserved | 71 | 51 |
| f_dpo | distorted | 18 | 0 |
| f_dpo | preserved | 54 | 31 |
| f_entry | lost | 2 | 0 |
| f_entry | preserved | 214 | 140 |
| f_first | lost | 18 | 13 |
| f_first | preserved | 54 | 37 |
| f_inactive | preserved | 72 | 33 |
| f_low_int | distorted | 1 | 0 |
| f_low_int | inverted | 1 | 0 |
| f_low_int | lost | 2 | 0 |
| f_low_int | preserved | 68 | 50 |
| f_low_iso | distorted | 1 | 0 |
| f_low_iso | preserved | 71 | 51 |
| f_low_order | lost | 2 | 0 |
| f_low_order | preserved | 70 | 48 |
| f_low_sorted | lost | 2 | 0 |
| f_low_sorted | preserved | 142 | 93 |
| f_low_tz | lost | 2 | 0 |
| f_low_tz | preserved | 70 | 30 |
| f_min | lost | 71 | 50 |
| f_min | preserved | 1 | 1 |
| f_no_both | lost | 2 | 0 |
| f_no_both | preserved | 70 | 47 |
| f_no_cancelled | distorted | 13 | 0 |
| f_no_cancelled | lost | 2 | 0 |
| f_no_cancelled | preserved | 57 | 46 |
| f_no_email | inverted | 47 | 0 |
| f_no_email | lost | 7 | 2 |
| f_no_email | preserved | 18 | 14 |
| f_no_email_log | distorted | 4 | 2 |
| f_no_email_log | inverted | 5 | 1 |
| f_no_email_log | lost | 2 | 0 |
| f_no_email_log | preserved | 61 | 50 |
| f_no_hold | preserved | 72 | 42 |
| f_no_past | distorted | 3 | 2 |
| f_no_past | lost | 2 | 0 |
| f_no_past | preserved | 67 | 46 |
| f_no_round_us | distorted | 2 | 0 |
| f_no_round_us | lost | 1 | 0 |
| f_no_round_us | preserved | 69 | 33 |
| f_no_staff | distorted | 4 | 0 |
| f_no_staff | preserved | 68 | 42 |
| f_no_trial | distorted | 2 | 1 |
| f_no_trial | preserved | 70 | 49 |
| f_no_vat_credit | inverted | 4 | 0 |
| f_no_vat_credit | lost | 1 | 0 |
| f_no_vat_credit | preserved | 67 | 45 |
| f_optout_field | lost | 1 | 0 |
| f_optout_field | preserved | 71 | 42 |
| f_period | distorted | 18 | 0 |
| f_period | lost | 51 | 30 |
| f_period | preserved | 3 | 2 |
| f_priority_closed | distorted | 5 | 0 |
| f_priority_closed | preserved | 67 | 38 |
| f_priority_date | distorted | 1 | 0 |
| f_priority_date | lost | 1 | 0 |
| f_priority_date | preserved | 70 | 51 |
| f_priority_time | lost | 2 | 0 |
| f_priority_time | preserved | 70 | 49 |
| f_quiet | distorted | 38 | 13 |
| f_quiet | lost | 22 | 12 |
| f_quiet | preserved | 12 | 8 |
| f_seat_field | lost | 1 | 0 |
| f_seat_field | preserved | 71 | 33 |
| f_second | lost | 18 | 13 |
| f_second | preserved | 54 | 37 |
| f_seen_field | preserved | 72 | 42 |
| f_signer | distorted | 18 | 0 |
| f_signer | lost | 2 | 0 |
| f_signer | preserved | 52 | 37 |
| f_signer_pl | lost | 2 | 0 |
| f_signer_pl | preserved | 70 | 48 |
| f_sms_len | lost | 2 | 0 |
| f_sms_len | preserved | 70 | 49 |
| f_vat_rate | lost | 70 | 50 |
| f_vat_rate | preserved | 2 | 0 |
| f_warn | distorted | 18 | 0 |
| f_warn | preserved | 54 | 33 |
| w_budget | lost | 2 | 0 |
| w_budget | preserved | 70 | 70 |
| w_ceremony | lost | 2 | 0 |
| w_ceremony | preserved | 70 | 68 |
| w_cond_cards | distorted | 27 | 27 |
| w_cond_cards | lost | 2 | 0 |
| w_cond_cards | preserved | 43 | 41 |
| w_cond_heat | distorted | 3 | 2 |
| w_cond_heat | lost | 2 | 0 |
| w_cond_heat | preserved | 67 | 65 |
| w_date | preserved | 72 | 69 |
| w_diet | distorted | 15 | 0 |
| w_diet | lost | 2 | 0 |
| w_diet | preserved | 55 | 55 |
| w_dinner | lost | 2 | 0 |
| w_dinner | preserved | 70 | 70 |
| w_grandmother | lost | 2 | 0 |
| w_grandmother | preserved | 70 | 67 |
| w_guests | lost | 2 | 0 |
| w_guests | preserved | 70 | 70 |
| w_interpreter | distorted | 17 | 0 |
| w_interpreter | lost | 2 | 0 |
| w_interpreter | preserved | 53 | 53 |
| w_low_dog | distorted | 17 | 0 |
| w_low_dog | lost | 3 | 0 |
| w_low_dog | preserved | 52 | 27 |
| w_low_hearing | distorted | 15 | 0 |
| w_low_hearing | lost | 2 | 0 |
| w_low_hearing | preserved | 55 | 53 |
| w_no_lumiere | distorted | 1 | 1 |
| w_no_lumiere | lost | 2 | 0 |
| w_no_lumiere | preserved | 69 | 69 |
| w_no_macarena | lost | 2 | 0 |
| w_no_macarena | preserved | 70 | 70 |
| w_no_nuts | lost | 2 | 0 |
| w_no_nuts | preserved | 70 | 51 |
| w_priority_interp | distorted | 16 | 16 |
| w_priority_interp | lost | 2 | 0 |
| w_priority_interp | preserved | 54 | 54 |
| w_priority_late | lost | 2 | 0 |
| w_priority_late | preserved | 70 | 70 |
| w_shuttle | lost | 2 | 0 |
| w_shuttle | preserved | 70 | 70 |
| w_venue | lost | 2 | 0 |
| w_venue | preserved | 70 | 70 |

## Plan consistency checks (untagged, not in the score)

| run_id | consistency |
|---|---|
| event_2-hier_chain-forward-asr_interpreter-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_2-hier_chain-forward-clean-gpt-6-luna | budget_total_within_cap=True |
| event_2-hier_chain-forward-clean-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_2-hier_chain-forward-homophone_children-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_2-hier_chain-forward-punct_cards-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_2-hier_chain-free-asr_interpreter-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_2-hier_chain-free-homophone_children-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_2-hier_chain-structured-asr_interpreter-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_2-hier_chain-structured-asr_interpreter-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_2-hier_chain-structured-clean-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_2-hier_chain-structured-homophone_children-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_2-hier_chain-structured-homophone_children-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_2-hier_chain-structured-punct_cards-gpt-6-luna | budget_total_within_cap=True |
| event_2-hier_chain-structured-punct_cards-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_2-hub_relay-forward-asr_interpreter-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_2-hub_relay-forward-asr_interpreter-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_2-hub_relay-forward-homophone_children-gpt-6-luna | budget_total_within_cap=True |
| event_2-hub_relay-forward-punct_cards-gpt-6-luna | budget_total_within_cap=True |
| event_2-hub_relay-forward-punct_cards-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_2-hub_relay-free-clean-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_2-hub_relay-free-punct_cards-gpt-6-luna | budget_total_within_cap=True |
| event_2-hub_relay-free-punct_cards-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_2-hub_relay-structured-asr_interpreter-gpt-6-luna | budget_total_within_cap=True |
| event_2-hub_relay-structured-asr_interpreter-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_2-hub_relay-structured-homophone_children-gpt-6-luna | budget_total_within_cap=True |
| event_2-hub_relay-structured-punct_cards-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hier_chain-forward-asr_av-gpt-6-luna | budget_total_within_cap=True |
| event_3-hier_chain-forward-asr_av-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hier_chain-forward-asr_av-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hier_chain-forward-clean-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hier_chain-forward-homophone_delegates-gpt-6-luna | budget_total_within_cap=True |
| event_3-hier_chain-forward-homophone_delegates-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hier_chain-forward-homophone_delegates-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hier_chain-forward-punct_record-gpt-6-luna | budget_total_within_cap=True |
| event_3-hier_chain-forward-punct_record-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hier_chain-forward-punct_record-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hier_chain-free-asr_av-gpt-6-luna | budget_total_within_cap=True |
| event_3-hier_chain-free-asr_av-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hier_chain-free-clean-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hier_chain-free-clean-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hier_chain-free-homophone_delegates-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hier_chain-free-homophone_delegates-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hier_chain-free-punct_record-gpt-6-luna | budget_total_within_cap=True |
| event_3-hier_chain-free-punct_record-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hier_chain-free-punct_record-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hier_chain-structured-asr_av-gpt-6-luna | budget_total_within_cap=True |
| event_3-hier_chain-structured-asr_av-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hier_chain-structured-clean-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hier_chain-structured-clean-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hier_chain-structured-homophone_delegates-gpt-6-luna | budget_total_within_cap=True |
| event_3-hier_chain-structured-homophone_delegates-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hier_chain-structured-punct_record-gpt-6-luna | budget_total_within_cap=True |
| event_3-hier_chain-structured-punct_record-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hub_relay-forward-asr_av-gpt-6-luna | budget_total_within_cap=True |
| event_3-hub_relay-forward-asr_av-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hub_relay-forward-asr_av-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hub_relay-forward-clean-gpt-6-luna | budget_total_within_cap=True |
| event_3-hub_relay-forward-clean-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hub_relay-forward-homophone_delegates-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hub_relay-forward-punct_record-gpt-6-luna | budget_total_within_cap=True |
| event_3-hub_relay-forward-punct_record-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hub_relay-free-asr_av-gpt-6-luna | budget_total_within_cap=True |
| event_3-hub_relay-free-asr_av-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hub_relay-free-asr_av-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hub_relay-free-clean-gpt-6-luna | budget_total_within_cap=True |
| event_3-hub_relay-free-homophone_delegates-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hub_relay-free-homophone_delegates-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hub_relay-free-punct_record-gpt-6-luna | budget_total_within_cap=True |
| event_3-hub_relay-structured-asr_av-gpt-6-luna | budget_total_within_cap=True |
| event_3-hub_relay-structured-asr_av-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hub_relay-structured-asr_av-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_3-hub_relay-structured-clean-gpt-6-luna | budget_total_within_cap=True |
| event_3-hub_relay-structured-clean-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hub_relay-structured-homophone_delegates-gpt-6-luna | budget_total_within_cap=True |
| event_3-hub_relay-structured-homophone_delegates-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hub_relay-structured-punct_record-gpt-6-luna | budget_total_within_cap=True |
| event_3-hub_relay-structured-punct_record-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_3-hub_relay-structured-punct_record-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hier_chain-forward-asr_cfo-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hier_chain-forward-asr_cfo-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hier_chain-forward-clean-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hier_chain-forward-homophone_guests-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hier_chain-forward-punct_alcohol-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hier_chain-free-asr_cfo-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hier_chain-free-asr_cfo-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hier_chain-free-clean-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hier_chain-free-clean-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_pilot-hier_chain-free-homophone_guests-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hier_chain-free-homophone_guests-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hier_chain-free-punct_alcohol-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hier_chain-free-punct_alcohol-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hier_chain-structured-asr_cfo-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_pilot-hier_chain-structured-clean-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hier_chain-structured-clean-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_pilot-hier_chain-structured-homophone_guests-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_pilot-hier_chain-structured-punct_alcohol-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hier_chain-structured-punct_alcohol-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-forward-asr_cfo-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-forward-clean-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hub_relay-forward-clean-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-forward-homophone_guests-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-forward-punct_alcohol-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hub_relay-free-asr_cfo-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hub_relay-free-asr_cfo-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-free-homophone_guests-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-asr_cfo-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-asr_cfo-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-asr_cfo-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-clean-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-clean-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-clean-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-homophone_guests-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-homophone_guests-gpt-6-luna-s1 | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-homophone_guests-gpt-6-luna-s2 | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-punct_alcohol-gpt-6-luna | budget_total_within_cap=True |
| event_pilot-hub_relay-structured-punct_alcohol-gpt-6-luna-s2 | budget_total_within_cap=True |

## H7: fact label at the last downward hand-off vs its endpoint check (note view)

Forward runs, loss-insensitive facts, facts failed only through a dependency and the noise-affected facts of noisy runs are excluded (their wrong reading propagates by design: see the per-fact table).

| label_at_last_handoff | facts | endpoint_pass_rate |
|---|---|---|
| distorted | 37 | 0.595 |
| inverted | 7 | 0.857 |
| lost | 7 | 0.857 |
| preserved | 3790 | 0.920 |

Per fact (noise-affected facts of noisy runs kept and flagged):

| fact_id | label_at_last_handoff | noise_affected | facts | passed | endpoint_pass_rate |
|---|---|---|---|---|---|
| c_av_contact | distorted | True | 12 | 0 | 0.000 |
| c_av_contact | preserved | False | 36 | 35 | 0.972 |
| c_budget | preserved | False | 48 | 47 | 0.979 |
| c_chair | distorted | False | 7 | 7 | 1.000 |
| c_chair | preserved | False | 41 | 40 | 0.976 |
| c_cond_overflow | preserved | False | 48 | 47 | 0.979 |
| c_cond_strike | distorted | False | 1 | 1 | 1.000 |
| c_cond_strike | preserved | False | 47 | 44 | 0.936 |
| c_date | preserved | False | 48 | 47 | 0.979 |
| c_delegates | distorted | True | 1 | 0 | 0.000 |
| c_delegates | preserved | False | 36 | 35 | 0.972 |
| c_delegates | preserved | True | 11 | 11 | 1.000 |
| c_keynote_speaker | preserved | False | 48 | 47 | 0.979 |
| c_keynote_time | preserved | False | 48 | 47 | 0.979 |
| c_low_lapel | preserved | False | 47 | 47 | 1.000 |
| c_low_ratio | preserved | False | 48 | 47 | 0.979 |
| c_lunch | preserved | False | 48 | 47 | 0.979 |
| c_no_coffee | preserved | False | 48 | 47 | 0.979 |
| c_no_flash | preserved | False | 48 | 47 | 0.979 |
| c_no_record | distorted | True | 1 | 0 | 0.000 |
| c_no_record | preserved | False | 36 | 35 | 0.972 |
| c_no_record | preserved | True | 11 | 11 | 1.000 |
| c_posters | preserved | False | 48 | 47 | 0.979 |
| c_priority_caption | preserved | False | 48 | 46 | 0.958 |
| c_priority_questions | distorted | False | 1 | 1 | 1.000 |
| c_priority_questions | preserved | False | 47 | 46 | 0.979 |
| c_venue | preserved | False | 48 | 47 | 0.979 |
| e_budget | preserved | False | 48 | 46 | 0.958 |
| e_ceo | preserved | False | 48 | 46 | 0.958 |
| e_coach_time | preserved | False | 48 | 46 | 0.958 |
| e_cond_coach | preserved | False | 48 | 46 | 0.958 |
| e_cond_rain | preserved | False | 48 | 46 | 0.958 |
| e_date | preserved | False | 48 | 46 | 0.958 |
| e_diet | preserved | False | 48 | 46 | 0.958 |
| e_dinner | preserved | False | 48 | 44 | 0.917 |
| e_guests | distorted | True | 12 | 0 | 0.000 |
| e_guests | preserved | False | 36 | 34 | 0.944 |
| e_low_lefty | preserved | False | 46 | 46 | 1.000 |
| e_low_step_free | distorted | True | 6 | 5 | 0.833 |
| e_low_step_free | preserved | False | 36 | 35 | 0.972 |
| e_low_step_free | preserved | True | 6 | 6 | 1.000 |
| e_no_alcohol | preserved | False | 36 | 35 | 0.972 |
| e_no_alcohol | preserved | True | 12 | 11 | 0.917 |
| e_no_coachline | preserved | False | 48 | 46 | 0.958 |
| e_no_shellfish | preserved | False | 48 | 22 | 0.458 |
| e_priority_band | preserved | False | 48 | 46 | 0.958 |
| e_priority_keynote | preserved | False | 48 | 46 | 0.958 |
| e_reception | preserved | False | 48 | 45 | 0.938 |
| e_speaker | preserved | False | 48 | 36 | 0.750 |
| e_venue | preserved | False | 48 | 46 | 0.958 |
| e_vip_cfo | distorted | True | 12 | 0 | 0.000 |
| e_vip_cfo | preserved | False | 36 | 35 | 0.972 |
| f_approver | distorted | True | 7 | 0 | 0.000 |
| f_approver | preserved | False | 22 | 21 | 0.955 |
| f_approver_big | distorted | False | 3 | 0 | 0.000 |
| f_approver_big | preserved | False | 26 | 25 | 0.962 |
| f_batch | preserved | False | 18 | 18 | 1.000 |
| f_closed | preserved | False | 18 | 17 | 0.944 |
| f_cond_big | distorted | False | 3 | 0 | 0.000 |
| f_cond_big | preserved | False | 26 | 25 | 0.962 |
| f_cond_channel | inverted | True | 6 | 1 | 0.167 |
| f_cond_channel | preserved | False | 20 | 19 | 0.950 |
| f_cond_downgrade | distorted | False | 1 | 1 | 1.000 |
| f_cond_downgrade | preserved | False | 28 | 27 | 0.964 |
| f_cond_invoice | preserved | False | 18 | 18 | 1.000 |
| f_cond_late | distorted | False | 1 | 1 | 1.000 |
| f_cond_late | preserved | False | 25 | 25 | 1.000 |
| f_cond_pl | preserved | False | 26 | 26 | 1.000 |
| f_cond_vat | preserved | False | 29 | 29 | 1.000 |
| f_cond_warn | preserved | False | 13 | 12 | 0.923 |
| f_cond_warn | preserved | True | 5 | 5 | 1.000 |
| f_desc_len | preserved | False | 29 | 29 | 1.000 |
| f_dpo | distorted | True | 5 | 0 | 0.000 |
| f_dpo | preserved | False | 13 | 8 | 0.615 |
| f_entry | preserved | False | 144 | 73 | 0.507 |
| f_first | preserved | False | 26 | 26 | 1.000 |
| f_inactive | preserved | False | 18 | 15 | 0.833 |
| f_low_int | lost | False | 1 | 1 | 1.000 |
| f_low_int | preserved | False | 28 | 27 | 0.964 |
| f_low_iso | lost | False | 1 | 0 | 0.000 |
| f_low_iso | preserved | False | 17 | 17 | 1.000 |
| f_low_sorted | preserved | False | 44 | 44 | 1.000 |
| f_low_tz | preserved | False | 26 | 15 | 0.577 |
| f_min | distorted | False | 6 | 6 | 1.000 |
| f_min | lost | False | 1 | 1 | 1.000 |
| f_min | preserved | False | 22 | 22 | 1.000 |
| f_no_cancelled | preserved | False | 26 | 24 | 0.923 |
| f_no_email | preserved | False | 18 | 3 | 0.167 |
| f_no_email_log | preserved | False | 26 | 23 | 0.885 |
| f_no_hold | preserved | False | 18 | 18 | 1.000 |
| f_no_past | inverted | False | 1 | 1 | 1.000 |
| f_no_past | preserved | False | 25 | 25 | 1.000 |
| f_no_round_us | inverted | False | 6 | 5 | 0.833 |
| f_no_round_us | preserved | False | 23 | 15 | 0.652 |
| f_no_staff | preserved | False | 18 | 18 | 1.000 |
| f_no_trial | preserved | False | 23 | 22 | 0.957 |
| f_no_trial | preserved | True | 6 | 6 | 1.000 |
| f_no_vat_credit | preserved | False | 29 | 28 | 0.966 |
| f_optout_field | preserved | False | 26 | 21 | 0.808 |
| f_period | distorted | True | 8 | 0 | 0.000 |
| f_period | preserved | False | 21 | 20 | 0.952 |
| f_priority_closed | distorted | False | 2 | 0 | 0.000 |
| f_priority_closed | preserved | False | 16 | 14 | 0.875 |
| f_priority_date | preserved | False | 29 | 29 | 1.000 |
| f_priority_time | preserved | False | 26 | 26 | 1.000 |
| f_quiet | distorted | False | 11 | 5 | 0.455 |
| f_quiet | preserved | False | 15 | 12 | 0.800 |
| f_seat_field | preserved | False | 29 | 20 | 0.690 |
| f_second | preserved | False | 20 | 20 | 1.000 |
| f_second | preserved | True | 6 | 6 | 1.000 |
| f_seen_field | preserved | False | 18 | 18 | 1.000 |
| f_signer | distorted | True | 7 | 0 | 0.000 |
| f_signer | preserved | False | 19 | 19 | 1.000 |
| f_signer_pl | preserved | False | 26 | 26 | 1.000 |
| f_sms_len | preserved | False | 26 | 26 | 1.000 |
| f_vat_rate | preserved | False | 29 | 29 | 1.000 |
| f_warn | distorted | True | 1 | 0 | 0.000 |
| f_warn | preserved | False | 15 | 15 | 1.000 |
| f_warn | preserved | True | 2 | 0 | 0.000 |
| w_budget | lost | False | 2 | 2 | 1.000 |
| w_budget | preserved | False | 46 | 45 | 0.978 |
| w_ceremony | preserved | False | 48 | 45 | 0.938 |
| w_cond_cards | preserved | False | 36 | 33 | 0.917 |
| w_cond_cards | preserved | True | 12 | 12 | 1.000 |
| w_cond_heat | preserved | False | 48 | 45 | 0.938 |
| w_date | lost | False | 2 | 2 | 1.000 |
| w_date | preserved | False | 46 | 44 | 0.957 |
| w_diet | distorted | True | 9 | 0 | 0.000 |
| w_diet | lost | True | 3 | 0 | 0.000 |
| w_diet | preserved | False | 36 | 35 | 0.972 |
| w_dinner | preserved | False | 48 | 47 | 0.979 |
| w_grandmother | preserved | False | 48 | 44 | 0.917 |
| w_guests | preserved | False | 48 | 47 | 0.979 |
| w_interpreter | distorted | True | 12 | 0 | 0.000 |
| w_interpreter | preserved | False | 36 | 36 | 1.000 |
| w_low_dog | distorted | False | 1 | 0 | 0.000 |
| w_low_dog | preserved | False | 47 | 19 | 0.404 |
| w_low_hearing | preserved | False | 34 | 34 | 1.000 |
| w_no_lumiere | preserved | False | 48 | 47 | 0.979 |
| w_no_macarena | preserved | False | 48 | 47 | 0.979 |
| w_no_nuts | preserved | False | 48 | 37 | 0.771 |
| w_priority_interp | preserved | False | 48 | 47 | 0.979 |
| w_priority_late | preserved | False | 48 | 47 | 0.979 |
| w_shuttle | preserved | False | 48 | 47 | 0.979 |
| w_venue | preserved | False | 48 | 47 | 0.979 |

## Hand-off output tokens (per message, from the stream; see runner_cc.turn_usage)

| model | direction | messages | median_output_tokens | total_output_tokens | estimated_share |
|---|---|---|---|---|---|
| gpt-6-luna | down | 972 | 395.000 | 428641 | 0.000 |
| gpt-6-luna | up | 216 | 504.000 | 115763 | 0.000 |

## Invented claims by distance (judge, note view)

| kind | distance | messages | invented | per_message |
|---|---|---|---|---|
| source | 1 | 432 | 90 | 0.208 |
| handoff | 2 | 432 | 197 | 0.456 |
| handoff | 3 | 432 | 598 | 1.384 |
| endpoint | 4 | 108 | 475 | 4.398 |
| handoff | 4 | 324 | 773 | 2.386 |
| endpoint | 5 | 324 | 1077 | 3.324 |
