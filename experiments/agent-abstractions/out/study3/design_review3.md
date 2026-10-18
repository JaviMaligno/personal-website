# Study 3 design review (H1)

## Reliability (second judge, 340 packets, 24 T0)

| question | n | kappa | kind | raw agreement |
|---|---|---|---|---|
| reuse | 316 | 0.842 | qwk | 0.722 |
| duplication | 316 | 0.888 | qwk | 0.722 |
| placement | 316 | 0.815 | qwk | 0.772 |
| scope | 316 | 0.702 | qwk | 0.801 |
| maintainability | 316 | 0.872 | qwk | 0.753 |
| interface | 24 | 0.847 | qwk | 0.833 |
| completeness | 24 | 1.0 | qwk | 1.0 |
| t2_reuse | 67 | 0.709 | nominal | 0.881 |
| one_place | 114 | 0.903 | nominal | 0.956 |
| disguised_duplication | 340 | 0.707 | nominal | 0.894 |
| bypasses_abstraction | 316 | 0.761 | nominal | 0.896 |
| would_merge | 316 | 0.751 | nominal | 0.87 |
| abstraction_drift | 76 | 0.723 | nominal | 0.882 |

## claude

Chain packets (T1–T4 diff; RC from its T0 tree). Primary: maintainability.

| arm | vs | scope | metric | arm mean (n) | ref mean (n) | MW p | zones +/− | sign p |
|---|---|---|---|---|---|---|---|---|
| RG | R | all | reuse | 3.469 (32) | 3.156 (32) | 0.0669 | 3/1 | 0.625 |
| RG | R | all | duplication | 2.75 (32) | 2.438 (32) | 0.1156 | 3/1 | 0.625 |
| RG | R | all | placement | 4 (32) | 3.938 (32) | 0.7171 | 2/1 | 1.0 |
| RG | R | all | scope | 4.344 (32) | 4.125 (32) | 0.0685 | 3/1 | 0.625 |
| RG | R | all | maintainability | 3.094 (32) | 2.594 (32) | 0.0046 | 4/0 | 0.125 |
| RG | R | all | duplicated_blocks | 2.031 (32) | 2.625 (32) | 0.0571 | 0/3 | 0.25 |
| RG | R | without_Z4 | reuse | 3.458 (24) | 3.167 (24) | 0.1945 | 2/1 | 1.0 |
| RG | R | without_Z4 | duplication | 2.833 (24) | 2.542 (24) | 0.24 | 2/1 | 1.0 |
| RG | R | without_Z4 | placement | 4.125 (24) | 4.125 (24) | 0.9814 | 1/1 | 1.0 |
| RG | R | without_Z4 | scope | 4.208 (24) | 4.125 (24) | 0.5386 | 2/1 | 1.0 |
| RG | R | without_Z4 | maintainability | 3.083 (24) | 2.667 (24) | 0.0648 | 3/0 | 0.25 |
| RG | R | without_Z4 | duplicated_blocks | 1.958 (24) | 2.5 (24) | 0.2019 | 0/2 | 0.5 |
| RG | F | all | reuse | 3.469 (32) | 3.906 (32) | 0.0564 | 0/4 | 0.125 |
| RG | F | all | duplication | 2.75 (32) | 3.344 (32) | 0.0641 | 0/3 | 0.25 |
| RG | F | all | placement | 4 (32) | 4.156 (32) | 0.3616 | 1/3 | 0.625 |
| RG | F | all | scope | 4.344 (32) | 4.031 (32) | 0.0176 | 3/0 | 0.25 |
| RG | F | all | maintainability | 3.094 (32) | 3.406 (32) | 0.0547 | 1/3 | 0.625 |
| RG | F | all | duplicated_blocks | 2.031 (32) | 1.531 (32) | 0.1064 | 2/2 | 1.0 |
| RG | F | without_Z4 | reuse | 3.458 (24) | 3.958 (24) | 0.0913 | 0/3 | 0.25 |
| RG | F | without_Z4 | duplication | 2.833 (24) | 3.625 (24) | 0.0306 | 0/3 | 0.25 |
| RG | F | without_Z4 | placement | 4.125 (24) | 4.292 (24) | 0.3298 | 1/2 | 1.0 |
| RG | F | without_Z4 | scope | 4.208 (24) | 3.958 (24) | 0.0837 | 2/0 | 0.5 |
| RG | F | without_Z4 | maintainability | 3.083 (24) | 3.542 (24) | 0.0236 | 0/3 | 0.25 |
| RG | F | without_Z4 | duplicated_blocks | 1.958 (24) | 1.25 (24) | 0.0337 | 2/1 | 1.0 |
| RL | R | all | reuse | 3.75 (32) | 3.156 (32) | 0.0008 | 3/1 | 0.625 |
| RL | R | all | duplication | 3.156 (32) | 2.438 (32) | 0.0018 | 3/1 | 0.625 |
| RL | R | all | placement | 4.062 (32) | 3.938 (32) | 0.5007 | 2/1 | 1.0 |
| RL | R | all | scope | 3.969 (32) | 4.125 (32) | 0.2106 | 0/2 | 0.5 |
| RL | R | all | maintainability | 3.188 (32) | 2.594 (32) | 0.0126 | 3/1 | 0.625 |
| RL | R | all | duplicated_blocks | 1.594 (32) | 2.625 (32) | 0.0015 | 0/4 | 0.125 |
| RL | R | without_Z4 | reuse | 4 (24) | 3.167 (24) | 0.0001 | 3/0 | 0.25 |
| RL | R | without_Z4 | duplication | 3.542 (24) | 2.542 (24) | 0.0004 | 3/0 | 0.25 |
| RL | R | without_Z4 | placement | 4.417 (24) | 4.125 (24) | 0.1375 | 2/0 | 0.5 |
| RL | R | without_Z4 | scope | 3.958 (24) | 4.125 (24) | 0.308 | 0/1 | 1.0 |
| RL | R | without_Z4 | maintainability | 3.583 (24) | 2.667 (24) | 0.0002 | 3/0 | 0.25 |
| RL | R | without_Z4 | duplicated_blocks | 1.167 (24) | 2.5 (24) | 0.0014 | 0/3 | 0.25 |
| RL | R | non_blind | reuse | 4.125 (16) | 2.938 (16) | 0.0 | 2/0 | 0.5 |
| RL | R | non_blind | duplication | 3.438 (16) | 2.125 (16) | 0.0 | 2/0 | 0.5 |
| RL | R | non_blind | placement | 4.25 (16) | 3.938 (16) | 0.1094 | 1/0 | 1.0 |
| RL | R | non_blind | scope | 3.812 (16) | 4.062 (16) | 0.2045 | 0/1 | 1.0 |
| RL | R | non_blind | maintainability | 3.688 (16) | 2.562 (16) | 0.0011 | 2/0 | 0.5 |
| RL | R | non_blind | duplicated_blocks | 1.438 (16) | 3.062 (16) | 0.0003 | 0/2 | 0.5 |
| RL | F | all | reuse | 3.75 (32) | 3.906 (32) | 0.5126 | 1/3 | 0.625 |
| RL | F | all | duplication | 3.156 (32) | 3.344 (32) | 0.6058 | 1/3 | 0.625 |
| RL | F | all | placement | 4.062 (32) | 4.156 (32) | 0.6279 | 1/3 | 0.625 |
| RL | F | all | scope | 3.969 (32) | 4.031 (32) | 0.6261 | 2/2 | 1.0 |
| RL | F | all | maintainability | 3.188 (32) | 3.406 (32) | 0.3151 | 1/3 | 0.625 |
| RL | F | all | duplicated_blocks | 1.594 (32) | 1.531 (32) | 0.7041 | 3/1 | 0.625 |
| RL | F | without_Z4 | reuse | 4 (24) | 3.958 (24) | 0.8349 | 1/2 | 1.0 |
| RL | F | without_Z4 | duplication | 3.542 (24) | 3.625 (24) | 0.5919 | 1/2 | 1.0 |
| RL | F | without_Z4 | placement | 4.417 (24) | 4.292 (24) | 0.7218 | 1/2 | 1.0 |
| RL | F | without_Z4 | scope | 3.958 (24) | 3.958 (24) | 0.9897 | 2/1 | 1.0 |
| RL | F | without_Z4 | maintainability | 3.583 (24) | 3.542 (24) | 0.8912 | 1/2 | 1.0 |
| RL | F | without_Z4 | duplicated_blocks | 1.167 (24) | 1.25 (24) | 0.5912 | 2/1 | 1.0 |
| RL | F | non_blind | reuse | 4.125 (16) | 3.562 (16) | 0.0314 | 1/1 | 1.0 |
| RL | F | non_blind | duplication | 3.438 (16) | 3.062 (16) | 0.258 | 1/1 | 1.0 |
| RL | F | non_blind | placement | 4.25 (16) | 4 (16) | 0.3029 | 1/1 | 1.0 |
| RL | F | non_blind | scope | 3.812 (16) | 4 (16) | 0.3577 | 1/1 | 1.0 |
| RL | F | non_blind | maintainability | 3.688 (16) | 3.438 (16) | 0.3737 | 1/1 | 1.0 |
| RL | F | non_blind | duplicated_blocks | 1.438 (16) | 1.875 (16) | 0.4581 | 1/1 | 1.0 |
| RC | R | all | reuse | 3.812 (32) | 3.156 (32) | 0.0005 | 4/0 | 0.125 |
| RC | R | all | duplication | 2.969 (32) | 2.438 (32) | 0.0141 | 4/0 | 0.125 |
| RC | R | all | placement | 4.031 (32) | 3.938 (32) | 0.6477 | 3/1 | 0.625 |
| RC | R | all | scope | 4.375 (32) | 4.125 (32) | 0.0402 | 4/0 | 0.125 |
| RC | R | all | maintainability | 3.062 (32) | 2.594 (32) | 0.0167 | 4/0 | 0.125 |
| RC | R | all | duplicated_blocks | 2.031 (32) | 2.625 (32) | 0.0681 | 1/3 | 0.625 |
| RC | R | without_Z4 | reuse | 3.833 (24) | 3.167 (24) | 0.0043 | 3/0 | 0.25 |
| RC | R | without_Z4 | duplication | 3.167 (24) | 2.542 (24) | 0.0256 | 3/0 | 0.25 |
| RC | R | without_Z4 | placement | 4.208 (24) | 4.125 (24) | 0.5965 | 2/1 | 1.0 |
| RC | R | without_Z4 | scope | 4.375 (24) | 4.125 (24) | 0.0865 | 3/0 | 0.25 |
| RC | R | without_Z4 | maintainability | 3.208 (24) | 2.667 (24) | 0.0197 | 3/0 | 0.25 |
| RC | R | without_Z4 | duplicated_blocks | 1.917 (24) | 2.5 (24) | 0.18 | 1/2 | 1.0 |
| RC | F | all | reuse | 3.812 (32) | 3.906 (32) | 0.7536 | 1/1 | 1.0 |
| RC | F | all | duplication | 2.969 (32) | 3.344 (32) | 0.25 | 1/3 | 0.625 |
| RC | F | all | placement | 4.031 (32) | 4.156 (32) | 0.5772 | 0/3 | 0.25 |
| RC | F | all | scope | 4.375 (32) | 4.031 (32) | 0.01 | 4/0 | 0.125 |
| RC | F | all | maintainability | 3.062 (32) | 3.406 (32) | 0.0679 | 0/4 | 0.125 |
| RC | F | all | duplicated_blocks | 2.031 (32) | 1.531 (32) | 0.1399 | 3/0 | 0.25 |
| RC | F | without_Z4 | reuse | 3.833 (24) | 3.958 (24) | 0.7187 | 1/1 | 1.0 |
| RC | F | without_Z4 | duplication | 3.167 (24) | 3.625 (24) | 0.1471 | 1/2 | 1.0 |
| RC | F | without_Z4 | placement | 4.208 (24) | 4.292 (24) | 0.8408 | 0/2 | 0.5 |
| RC | F | without_Z4 | scope | 4.375 (24) | 3.958 (24) | 0.0087 | 3/0 | 0.25 |
| RC | F | without_Z4 | maintainability | 3.208 (24) | 3.542 (24) | 0.1327 | 0/3 | 0.25 |
| RC | F | without_Z4 | duplicated_blocks | 1.917 (24) | 1.25 (24) | 0.0534 | 3/0 | 0.25 |

RC T0..T4 (secondary) vs R:

- all: maintainability 3.25 (32) vs 2.594 (32), MW p=0.0006
- without_Z4: maintainability 3.458 (24) vs 2.667 (24), MW p=0.0004

## codex

Chain packets (T1–T4 diff; RC from its T0 tree). Primary: maintainability.

| arm | vs | scope | metric | arm mean (n) | ref mean (n) | MW p | zones +/− | sign p |
|---|---|---|---|---|---|---|---|---|
| RG | R | all | reuse | 2.5 (32) | 2.594 (32) | 0.6722 | 0/1 | 1.0 |
| RG | R | all | duplication | 2.031 (32) | 1.969 (32) | 0.5549 | 2/1 | 1.0 |
| RG | R | all | placement | 3.281 (32) | 3.5 (32) | 0.2931 | 0/2 | 0.5 |
| RG | R | all | scope | 4.031 (32) | 4.188 (32) | 0.3224 | 0/1 | 1.0 |
| RG | R | all | maintainability | 2.156 (32) | 2.188 (32) | 0.875 | 1/1 | 1.0 |
| RG | R | all | duplicated_blocks | 2.844 (32) | 2.969 (32) | 0.3557 | 1/3 | 0.625 |
| RG | R | without_Z4 | reuse | 2.375 (24) | 2.5 (24) | 0.617 | 0/1 | 1.0 |
| RG | R | without_Z4 | duplication | 2.042 (24) | 1.917 (24) | 0.4288 | 2/0 | 0.5 |
| RG | R | without_Z4 | placement | 3.333 (24) | 3.625 (24) | 0.2323 | 0/2 | 0.5 |
| RG | R | without_Z4 | scope | 4 (24) | 4.208 (24) | 0.3074 | 0/1 | 1.0 |
| RG | R | without_Z4 | maintainability | 2.208 (24) | 2.25 (24) | 0.885 | 1/1 | 1.0 |
| RG | R | without_Z4 | duplicated_blocks | 2.958 (24) | 3.083 (24) | 0.4696 | 1/2 | 1.0 |
| RG | F | all | reuse | 2.5 (32) | 3.375 (32) | 0.0004 | 1/3 | 0.625 |
| RG | F | all | duplication | 2.031 (32) | 2.969 (32) | 0.0001 | 1/3 | 0.625 |
| RG | F | all | placement | 3.281 (32) | 3.531 (32) | 0.4258 | 2/2 | 1.0 |
| RG | F | all | scope | 4.031 (32) | 4.25 (32) | 0.1656 | 1/3 | 0.625 |
| RG | F | all | maintainability | 2.156 (32) | 2.781 (32) | 0.004 | 0/3 | 0.25 |
| RG | F | all | duplicated_blocks | 2.844 (32) | 1.656 (32) | 0.0012 | 3/1 | 0.625 |
| RG | F | without_Z4 | reuse | 2.375 (24) | 3.583 (24) | 0.0001 | 0/3 | 0.25 |
| RG | F | without_Z4 | duplication | 2.042 (24) | 3.333 (24) | 0.0 | 0/3 | 0.25 |
| RG | F | without_Z4 | placement | 3.333 (24) | 3.708 (24) | 0.265 | 1/2 | 1.0 |
| RG | F | without_Z4 | scope | 4 (24) | 4.333 (24) | 0.1008 | 0/3 | 0.25 |
| RG | F | without_Z4 | maintainability | 2.208 (24) | 3.042 (24) | 0.0014 | 0/3 | 0.25 |
| RG | F | without_Z4 | duplicated_blocks | 2.958 (24) | 1.25 (24) | 0.0001 | 3/0 | 0.25 |
| RL | R | all | reuse | 2.812 (32) | 2.594 (32) | 0.2461 | 3/1 | 0.625 |
| RL | R | all | duplication | 2.344 (32) | 1.969 (32) | 0.0122 | 3/0 | 0.25 |
| RL | R | all | placement | 3.312 (32) | 3.5 (32) | 0.3111 | 1/3 | 0.625 |
| RL | R | all | scope | 3.938 (32) | 4.188 (32) | 0.0859 | 1/3 | 0.625 |
| RL | R | all | maintainability | 2.344 (32) | 2.188 (32) | 0.4276 | 2/1 | 1.0 |
| RL | R | all | duplicated_blocks | 2.312 (32) | 2.969 (32) | 0.01 | 0/3 | 0.25 |
| RL | R | without_Z4 | reuse | 2.833 (24) | 2.5 (24) | 0.1395 | 3/0 | 0.25 |
| RL | R | without_Z4 | duplication | 2.417 (24) | 1.917 (24) | 0.0095 | 3/0 | 0.25 |
| RL | R | without_Z4 | placement | 3.417 (24) | 3.625 (24) | 0.3631 | 1/2 | 1.0 |
| RL | R | without_Z4 | scope | 3.833 (24) | 4.208 (24) | 0.0404 | 0/3 | 0.25 |
| RL | R | without_Z4 | maintainability | 2.458 (24) | 2.25 (24) | 0.4219 | 2/1 | 1.0 |
| RL | R | without_Z4 | duplicated_blocks | 2.208 (24) | 3.083 (24) | 0.0069 | 0/3 | 0.25 |
| RL | R | non_blind | reuse | 3 (16) | 2.75 (16) | 0.1705 | 2/0 | 0.5 |
| RL | R | non_blind | duplication | 2.312 (16) | 1.875 (16) | 0.0412 | 2/0 | 0.5 |
| RL | R | non_blind | placement | 3.25 (16) | 3.688 (16) | 0.0777 | 0/2 | 0.5 |
| RL | R | non_blind | scope | 3.688 (16) | 4.188 (16) | 0.0167 | 0/2 | 0.5 |
| RL | R | non_blind | maintainability | 2.562 (16) | 2.5 (16) | 1.0 | 1/1 | 1.0 |
| RL | R | non_blind | duplicated_blocks | 2.5 (16) | 3.188 (16) | 0.0529 | 0/2 | 0.5 |
| RL | F | all | reuse | 2.812 (32) | 3.375 (32) | 0.0074 | 0/3 | 0.25 |
| RL | F | all | duplication | 2.344 (32) | 2.969 (32) | 0.0086 | 1/3 | 0.625 |
| RL | F | all | placement | 3.312 (32) | 3.531 (32) | 0.4568 | 0/2 | 0.5 |
| RL | F | all | scope | 3.938 (32) | 4.25 (32) | 0.0314 | 1/3 | 0.625 |
| RL | F | all | maintainability | 2.344 (32) | 2.781 (32) | 0.0275 | 0/3 | 0.25 |
| RL | F | all | duplicated_blocks | 2.312 (32) | 1.656 (32) | 0.0259 | 2/2 | 1.0 |
| RL | F | without_Z4 | reuse | 2.833 (24) | 3.583 (24) | 0.0027 | 0/3 | 0.25 |
| RL | F | without_Z4 | duplication | 2.417 (24) | 3.333 (24) | 0.0004 | 0/3 | 0.25 |
| RL | F | without_Z4 | placement | 3.417 (24) | 3.708 (24) | 0.3942 | 0/2 | 0.5 |
| RL | F | without_Z4 | scope | 3.833 (24) | 4.333 (24) | 0.0066 | 0/3 | 0.25 |
| RL | F | without_Z4 | maintainability | 2.458 (24) | 3.042 (24) | 0.0099 | 0/3 | 0.25 |
| RL | F | without_Z4 | duplicated_blocks | 2.208 (24) | 1.25 (24) | 0.0016 | 2/1 | 1.0 |
| RL | F | non_blind | reuse | 3 (16) | 3.812 (16) | 0.0029 | 0/2 | 0.5 |
| RL | F | non_blind | duplication | 2.312 (16) | 3.438 (16) | 0.0005 | 0/2 | 0.5 |
| RL | F | non_blind | placement | 3.25 (16) | 3.688 (16) | 0.2987 | 0/2 | 0.5 |
| RL | F | non_blind | scope | 3.688 (16) | 4.312 (16) | 0.0087 | 0/2 | 0.5 |
| RL | F | non_blind | maintainability | 2.562 (16) | 3.25 (16) | 0.0086 | 0/2 | 0.5 |
| RL | F | non_blind | duplicated_blocks | 2.5 (16) | 1.438 (16) | 0.02 | 1/1 | 1.0 |
| RC | R | all | reuse | 3.438 (32) | 2.594 (32) | 0.0 | 4/0 | 0.125 |
| RC | R | all | duplication | 2.562 (32) | 1.969 (32) | 0.0009 | 3/0 | 0.25 |
| RC | R | all | placement | 3.5 (32) | 3.5 (32) | 0.822 | 2/1 | 1.0 |
| RC | R | all | scope | 4.25 (32) | 4.188 (32) | 0.9544 | 2/2 | 1.0 |
| RC | R | all | maintainability | 2.594 (32) | 2.188 (32) | 0.0232 | 4/0 | 0.125 |
| RC | R | all | duplicated_blocks | 2.281 (32) | 2.969 (32) | 0.0218 | 1/3 | 0.625 |
| RC | R | without_Z4 | reuse | 3.542 (24) | 2.5 (24) | 0.0001 | 3/0 | 0.25 |
| RC | R | without_Z4 | duplication | 2.708 (24) | 1.917 (24) | 0.0006 | 3/0 | 0.25 |
| RC | R | without_Z4 | placement | 3.625 (24) | 3.625 (24) | 0.859 | 2/1 | 1.0 |
| RC | R | without_Z4 | scope | 4.25 (24) | 4.208 (24) | 0.837 | 1/2 | 1.0 |
| RC | R | without_Z4 | maintainability | 2.75 (24) | 2.25 (24) | 0.0266 | 3/0 | 0.25 |
| RC | R | without_Z4 | duplicated_blocks | 2.25 (24) | 3.083 (24) | 0.0317 | 1/2 | 1.0 |
| RC | F | all | reuse | 3.438 (32) | 3.375 (32) | 0.6912 | 2/2 | 1.0 |
| RC | F | all | duplication | 2.562 (32) | 2.969 (32) | 0.0797 | 2/2 | 1.0 |
| RC | F | all | placement | 3.5 (32) | 3.531 (32) | 0.9942 | 1/1 | 1.0 |
| RC | F | all | scope | 4.25 (32) | 4.25 (32) | 0.7 | 2/2 | 1.0 |
| RC | F | all | maintainability | 2.594 (32) | 2.781 (32) | 0.4029 | 1/2 | 1.0 |
| RC | F | all | duplicated_blocks | 2.281 (32) | 1.656 (32) | 0.082 | 2/2 | 1.0 |
| RC | F | without_Z4 | reuse | 3.542 (24) | 3.583 (24) | 0.9192 | 1/2 | 1.0 |
| RC | F | without_Z4 | duplication | 2.708 (24) | 3.333 (24) | 0.0113 | 1/2 | 1.0 |
| RC | F | without_Z4 | placement | 3.625 (24) | 3.708 (24) | 0.8439 | 0/1 | 1.0 |
| RC | F | without_Z4 | scope | 4.25 (24) | 4.333 (24) | 0.3183 | 1/2 | 1.0 |
| RC | F | without_Z4 | maintainability | 2.75 (24) | 3.042 (24) | 0.1634 | 0/2 | 0.5 |
| RC | F | without_Z4 | duplicated_blocks | 2.25 (24) | 1.25 (24) | 0.0118 | 2/1 | 1.0 |

RC T0..T4 (secondary) vs R:

- all: maintainability 2.594 (32) vs 2.188 (32), MW p=0.0585
- without_Z4: maintainability 2.792 (24) vs 2.25 (24), MW p=0.0351

## haiku

Chain packets (T1–T4 diff; RC from its T0 tree). Primary: maintainability.

| arm | vs | scope | metric | arm mean (n) | ref mean (n) | MW p | zones +/− | sign p |
|---|---|---|---|---|---|---|---|---|
| RG | R | all | reuse | 4.344 (32) | 4.062 (32) | 0.1265 | 3/1 | 0.625 |
| RG | R | all | duplication | 3.688 (32) | 3.344 (32) | 0.2383 | 3/1 | 0.625 |
| RG | R | all | placement | 4.531 (32) | 4.375 (32) | 0.2076 | 2/1 | 1.0 |
| RG | R | all | scope | 4.344 (32) | 4.438 (32) | 0.5273 | 2/2 | 1.0 |
| RG | R | all | maintainability | 3.781 (32) | 3.562 (32) | 0.1226 | 3/1 | 0.625 |
| RG | R | all | duplicated_blocks | 0.969 (32) | 1.469 (32) | 0.1075 | 1/3 | 0.625 |
| RG | R | without_Z4 | reuse | 4.333 (24) | 4.167 (24) | 0.4664 | 2/1 | 1.0 |
| RG | R | without_Z4 | duplication | 3.833 (24) | 3.542 (24) | 0.4041 | 2/1 | 1.0 |
| RG | R | without_Z4 | placement | 4.583 (24) | 4.5 (24) | 0.4824 | 1/1 | 1.0 |
| RG | R | without_Z4 | scope | 4.25 (24) | 4.458 (24) | 0.1916 | 1/2 | 1.0 |
| RG | R | without_Z4 | maintainability | 3.833 (24) | 3.75 (24) | 0.487 | 2/1 | 1.0 |
| RG | R | without_Z4 | duplicated_blocks | 0.875 (24) | 1.167 (24) | 0.4495 | 1/2 | 1.0 |
| RG | F | all | reuse | 4.344 (32) | 4.469 (32) | 0.8047 | 0/2 | 0.5 |
| RG | F | all | duplication | 3.688 (32) | 3.938 (32) | 0.4458 | 1/3 | 0.625 |
| RG | F | all | placement | 4.531 (32) | 4.531 (32) | 0.9016 | 2/1 | 1.0 |
| RG | F | all | scope | 4.344 (32) | 4 (32) | 0.0076 | 3/0 | 0.25 |
| RG | F | all | maintainability | 3.781 (32) | 3.906 (32) | 0.4958 | 1/3 | 0.625 |
| RG | F | all | duplicated_blocks | 0.969 (32) | 0.938 (32) | 0.8136 | 2/1 | 1.0 |
| RG | F | without_Z4 | reuse | 4.333 (24) | 4.5 (24) | 0.703 | 0/2 | 0.5 |
| RG | F | without_Z4 | duplication | 3.833 (24) | 4.208 (24) | 0.2956 | 0/3 | 0.25 |
| RG | F | without_Z4 | placement | 4.583 (24) | 4.625 (24) | 0.9221 | 1/1 | 1.0 |
| RG | F | without_Z4 | scope | 4.25 (24) | 3.875 (24) | 0.0064 | 2/0 | 0.5 |
| RG | F | without_Z4 | maintainability | 3.833 (24) | 4.083 (24) | 0.1653 | 0/3 | 0.25 |
| RG | F | without_Z4 | duplicated_blocks | 0.875 (24) | 0.708 (24) | 0.489 | 2/0 | 0.5 |
| RL | R | all | reuse | 4.25 (32) | 4.062 (32) | 0.3328 | 1/2 | 1.0 |
| RL | R | all | duplication | 3.812 (32) | 3.344 (32) | 0.1088 | 2/1 | 1.0 |
| RL | R | all | placement | 4.344 (32) | 4.375 (32) | 0.9761 | 2/2 | 1.0 |
| RL | R | all | scope | 4.125 (32) | 4.438 (32) | 0.0771 | 1/3 | 0.625 |
| RL | R | all | maintainability | 3.688 (32) | 3.562 (32) | 0.3815 | 2/1 | 1.0 |
| RL | R | all | duplicated_blocks | 1.031 (32) | 1.469 (32) | 0.1686 | 1/2 | 1.0 |
| RL | R | without_Z4 | reuse | 4.458 (24) | 4.167 (24) | 0.2484 | 1/1 | 1.0 |
| RL | R | without_Z4 | duplication | 4.167 (24) | 3.542 (24) | 0.068 | 2/1 | 1.0 |
| RL | R | without_Z4 | placement | 4.5 (24) | 4.5 (24) | 0.8967 | 2/1 | 1.0 |
| RL | R | without_Z4 | scope | 4.083 (24) | 4.458 (24) | 0.0911 | 1/2 | 1.0 |
| RL | R | without_Z4 | maintainability | 3.917 (24) | 3.75 (24) | 0.3301 | 2/1 | 1.0 |
| RL | R | without_Z4 | duplicated_blocks | 0.625 (24) | 1.167 (24) | 0.1606 | 1/1 | 1.0 |
| RL | R | non_blind | reuse | 4.188 (16) | 3.75 (16) | 0.1174 | 1/1 | 1.0 |
| RL | R | non_blind | duplication | 3.75 (16) | 2.875 (16) | 0.0194 | 1/1 | 1.0 |
| RL | R | non_blind | placement | 4.25 (16) | 4.438 (16) | 0.3805 | 1/1 | 1.0 |
| RL | R | non_blind | scope | 3.875 (16) | 4.5 (16) | 0.0239 | 0/2 | 0.5 |
| RL | R | non_blind | maintainability | 3.688 (16) | 3.562 (16) | 0.4352 | 1/1 | 1.0 |
| RL | R | non_blind | duplicated_blocks | 0.938 (16) | 1.75 (16) | 0.026 | 1/1 | 1.0 |
| RL | F | all | reuse | 4.25 (32) | 4.469 (32) | 0.4122 | 2/2 | 1.0 |
| RL | F | all | duplication | 3.812 (32) | 3.938 (32) | 0.8061 | 2/2 | 1.0 |
| RL | F | all | placement | 4.344 (32) | 4.531 (32) | 0.3132 | 2/2 | 1.0 |
| RL | F | all | scope | 4.125 (32) | 4 (32) | 0.3583 | 2/2 | 1.0 |
| RL | F | all | maintainability | 3.688 (32) | 3.906 (32) | 0.3144 | 2/2 | 1.0 |
| RL | F | all | duplicated_blocks | 1.031 (32) | 0.938 (32) | 0.7108 | 2/1 | 1.0 |
| RL | F | without_Z4 | reuse | 4.458 (24) | 4.5 (24) | 1.0 | 2/1 | 1.0 |
| RL | F | without_Z4 | duplication | 4.167 (24) | 4.208 (24) | 0.9205 | 2/1 | 1.0 |
| RL | F | without_Z4 | placement | 4.5 (24) | 4.625 (24) | 0.5021 | 2/1 | 1.0 |
| RL | F | without_Z4 | scope | 4.083 (24) | 3.875 (24) | 0.2483 | 2/1 | 1.0 |
| RL | F | without_Z4 | maintainability | 3.917 (24) | 4.083 (24) | 0.296 | 2/1 | 1.0 |
| RL | F | without_Z4 | duplicated_blocks | 0.625 (24) | 0.708 (24) | 0.836 | 1/1 | 1.0 |
| RL | F | non_blind | reuse | 4.188 (16) | 4.312 (16) | 0.6928 | 1/1 | 1.0 |
| RL | F | non_blind | duplication | 3.75 (16) | 3.875 (16) | 0.7627 | 1/1 | 1.0 |
| RL | F | non_blind | placement | 4.25 (16) | 4.625 (16) | 0.0684 | 1/1 | 1.0 |
| RL | F | non_blind | scope | 3.875 (16) | 3.812 (16) | 0.9485 | 1/1 | 1.0 |
| RL | F | non_blind | maintainability | 3.688 (16) | 4 (16) | 0.0983 | 1/1 | 1.0 |
| RL | F | non_blind | duplicated_blocks | 0.938 (16) | 1.062 (16) | 0.9673 | 1/1 | 1.0 |
| RC | R | all | reuse | 4.625 (32) | 4.062 (32) | 0.0036 | 3/1 | 0.625 |
| RC | R | all | duplication | 3.844 (32) | 3.344 (32) | 0.0597 | 3/1 | 0.625 |
| RC | R | all | placement | 4.75 (32) | 4.375 (32) | 0.0051 | 3/0 | 0.25 |
| RC | R | all | scope | 4.469 (32) | 4.438 (32) | 0.6523 | 2/1 | 1.0 |
| RC | R | all | maintainability | 3.906 (32) | 3.562 (32) | 0.0245 | 3/1 | 0.625 |
| RC | R | all | duplicated_blocks | 0.844 (32) | 1.469 (32) | 0.0488 | 2/2 | 1.0 |
| RC | R | without_Z4 | reuse | 4.625 (24) | 4.167 (24) | 0.0699 | 2/1 | 1.0 |
| RC | R | without_Z4 | duplication | 3.875 (24) | 3.542 (24) | 0.3954 | 2/1 | 1.0 |
| RC | R | without_Z4 | placement | 4.75 (24) | 4.5 (24) | 0.0788 | 2/0 | 0.5 |
| RC | R | without_Z4 | scope | 4.417 (24) | 4.458 (24) | 0.9907 | 1/1 | 1.0 |
| RC | R | without_Z4 | maintainability | 3.958 (24) | 3.75 (24) | 0.2089 | 2/1 | 1.0 |
| RC | R | without_Z4 | duplicated_blocks | 0.833 (24) | 1.167 (24) | 0.5846 | 2/1 | 1.0 |
| RC | F | all | reuse | 4.625 (32) | 4.469 (32) | 0.2803 | 3/1 | 0.625 |
| RC | F | all | duplication | 3.844 (32) | 3.938 (32) | 0.5693 | 1/3 | 0.625 |
| RC | F | all | placement | 4.75 (32) | 4.531 (32) | 0.1058 | 2/1 | 1.0 |
| RC | F | all | scope | 4.469 (32) | 4 (32) | 0.0007 | 4/0 | 0.125 |
| RC | F | all | maintainability | 3.906 (32) | 3.906 (32) | 0.9869 | 2/2 | 1.0 |
| RC | F | all | duplicated_blocks | 0.844 (32) | 0.938 (32) | 0.8573 | 2/2 | 1.0 |
| RC | F | without_Z4 | reuse | 4.625 (24) | 4.5 (24) | 0.5021 | 2/1 | 1.0 |
| RC | F | without_Z4 | duplication | 3.875 (24) | 4.208 (24) | 0.1265 | 0/3 | 0.25 |
| RC | F | without_Z4 | placement | 4.75 (24) | 4.625 (24) | 0.362 | 1/1 | 1.0 |
| RC | F | without_Z4 | scope | 4.417 (24) | 3.875 (24) | 0.0008 | 3/0 | 0.25 |
| RC | F | without_Z4 | maintainability | 3.958 (24) | 4.083 (24) | 0.4197 | 1/2 | 1.0 |
| RC | F | without_Z4 | duplicated_blocks | 0.833 (24) | 0.708 (24) | 0.1673 | 2/1 | 1.0 |

RC T0..T4 (secondary) vs R:

- all: maintainability 3.938 (32) vs 3.562 (32), MW p=0.0049
- without_Z4: maintainability 4.042 (24) vs 3.75 (24), MW p=0.0253

Nothing near p = 0.05 is read as an effect on its own.
