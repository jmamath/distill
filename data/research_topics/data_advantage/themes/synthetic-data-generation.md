---
id: synthetic-data-generation
name: Synthetic Data Generation
description: Model-generated training data for distillation, instruction tuning, textbook-style
  pretraining, and reasoning-trace transfer.
origin: bootstrap
novelty_status: globally_novel
key_entity_ids:
- self-instruct
- alpaca
- sharegpt
- phi
- orca
- cosmopedia
- deepseek-r1
- openai-o1
- openthoughts
- star-method
- shumailov-collapse
created_at: '2026-04-25'
updated_at: '2026-04-25'
---
Synthetic data has three genuinely different regimes, which are too often lumped together.

**Instruction distillation** — generate prompt/response pairs from a stronger model, fine-tune a weaker one. **Self-Instruct** (Wang et al., Dec 2022) bootstrapped 52K instructions from a seed model; **Alpaca** (Taori et al., Stanford, March 2023) applied it via text-davinci-003, and **Vicuna / ShareGPT** (LMSYS, March 2023) used scraped ChatGPT conversations. Alpaca cost $600 and spawned the open-instruction ecosystem. **WizardLM / Evol-Instruct** (Xu et al. 2023) iteratively complexified prompts; **Orca / Orca 2** (Mukherjee et al., Microsoft 2023) added GPT-4 explanation traces. These methods **reliably transfer instruction-following style and some task performance but do not transfer deep capabilities the teacher had from pretraining.**

**Textbook-style pretraining synthesis.** The **Phi series** (Gunasekar et al., "Textbooks Are All You Need," June 2023; through Phi-4, Dec 2024) argues that GPT-generated textbook-like pretraining data can produce small models punching well above their weight. Phi-3 (3.8B) and Phi-4 (14B) score competitively on MMLU and HumanEval at their scale. **This is the most contested line of work in data-centric AI.** Independent reproductions (TinyLlama, OpenPhi attempts) have not matched the reported numbers, and Phi's benchmark dominance doesn't consistently transfer to LMSYS Arena or harder reasoning benchmarks, raising concerns about benchmark-targeted synthesis. **Cosmopedia** (HuggingFace 2024, 25B synthetic tokens) and **WRAP / Rephrasing the Web** (Maini et al. 2024) are open implementations. Net: useful as a mixing ingredient at 10–30% of pretraining, not as a substitute.

**Reasoning-trace distillation.** This is the one synthetic regime with unambiguous, reproducible gains. **STaR** (Zelikman et al. 2022) pioneered generating chains-of-thought, filtering by answer correctness, and fine-tuning on the filtered set. **OpenAI o1** (Sept 2024) scaled this to RL on long CoTs, though training data remains closed. **DeepSeek-R1** (Jan 2025; Nature paper Sept 2025) made the recipe explicit: R1-Zero applies pure RL to DeepSeek-V3-Base with verifiable-reward tasks (math, code), producing emergent long CoT; R1 adds cold-start SFT; and **R1-distilled models** fine-tune Qwen/Llama bases on 800K curated R1 traces. Distilled DeepSeek-R1-Qwen-32B hit 72.6% AIME 2024 and 94.3% MATH-500, previously thought to require frontier-scale RL. The open community replicated the recipe within months: **OpenThoughts / OpenThinker3-7B** (June 2025, 1.2M traces from QwQ-32B, 53% AIME 2025), **Bespoke-Stratos**, **Sky-T1**, **AM-DeepSeek-R1-Distilled-1.4M**, and **NuminaMath-CoT**. Reasoning distillation now costs under $1K for 7B models and is arguably the largest shift in training economics since instruction tuning.

**The model-collapse debate.** Shumailov et al.'s Nature 2024 paper ("AI models collapse when trained on recursively generated data") demonstrated degeneration under recursive self-training. **Gerstgrasser et al. (2024), "Is Model Collapse Inevitable?", showed that if synthetic data is *accumulated* alongside real data rather than replacing it, collapse does not occur — which is what frontier labs actually do.** Collapse is a real risk for naive pipelines but not a ceiling on synthetic methods with grounded verifiers (math answer-checking, code execution, preference labels).