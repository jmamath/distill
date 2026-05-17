---
id: human-preference-alignment
name: Human-Preference and Alignment Data
description: >
  Preference datasets collected for RLHF, DPO, and constitutional-AI style
  training. Includes collection methodology, quality improvements, and the
  trade-offs between human annotation and AI-generated preference signals.
origin: bootstrap
novelty_status: globally_novel
key_entity_ids:
- instructgpt
- anthropic-hh
- constitutional-ai
- openassistant
- ultrafeedback
- dpo
- tulu
- helpsteer
- rewardbench
- prm800k
created_at: '2026-04-25'
updated_at: '2026-04-25'
---
Preference data is where explicit human labor meets the model — and therefore where budgets, IP, and demonstrable quality still differentiate labs.

**InstructGPT** (Ouyang et al., OpenAI Jan 2022) established the SFT→RM→PPO pipeline; the exact prompts and demonstrations remain proprietary. **Anthropic HH-RLHF** (Bai et al., April 2022, ~170K human preference comparisons for helpfulness and harmlessness) is the canonical open preference dataset. **Constitutional AI / RLAIF** (Bai et al., Dec 2022) showed model-written critiques can substitute for human red-team labels on harmlessness, with comparable results — the first evidence that AI feedback scales for alignment, foreshadowing UltraFeedback.

**OpenAssistant / OASST1-OASST2** (LAION, April 2023, ~161K messages across 66K conversation trees) was the community-sourced open analog. **UltraFeedback** (Cui et al., Oct 2023, 64K prompts × 4 responses × GPT-4 scores on four axes) became the default DPO dataset after **Zephyr-7B** (HuggingFace, Oct 2023) showed UltraFeedback+DPO beat RLHF baselines on MT-Bench. **DPO** itself (Rafailov et al., May 2023) collapsed the RM+PPO pipeline into a single contrastive loss and reshaped the economics — small teams can now align with ~10K preference pairs and a few GPU-hours.

**NVIDIA HelpSteer / HelpSteer2** (2023–2024) and **Nectar** (2023) extend multi-attribute labeling. **Tulu 2 / Tulu 3** (AI2, 2023–2024) are the most thoroughly documented open post-training pipelines, with Tulu 3's RLVR (RL with verifiable rewards) anticipating R1. **RewardBench** (Lambert et al., March 2024) finally provided a standardized evaluation for reward models, revealing that many open RMs are barely better than length-counting.

**Open debates:** Is DPO equivalent to PPO? (Evidence suggests yes on capability, no on robustness to distribution shift.) Does GPT-4-labeled preference data suffer from stylistic bias (length, formatting) that length-controls remove? (Yes, clearly.) Is there a preference-data-scaling law analogous to pretraining? (Unclear — gains saturate faster, and quality dominates quantity past ~50K pairs.)