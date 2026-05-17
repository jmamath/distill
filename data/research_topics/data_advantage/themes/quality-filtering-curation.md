---
id: quality-filtering-curation
name: Quality Filtering and Curation
description: >
  Advances in deduplication, quality scoring, contamination control, and
  data selection that improve training outcomes without requiring more raw
  data. Includes perplexity filtering, dedup algorithms, and curation
  pipelines like FineWeb and Dolma.
origin: bootstrap
novelty_status: globally_novel
key_entity_ids:
- c4
- refinedweb
- fineweb
- fineweb-edu
- dclm
- dolma
- redpajama
- nemotron-cc
- doremi
created_at: '2026-04-25'
updated_at: '2026-04-25'
---
Between 2021 and 2024, the field discovered that **most web tokens are noise, and intelligent removal beats addition.** Four pillars.

**Deduplication.** Lee et al. (2021), "Deduplicating Training Data Makes Language Models Better," showed exact and near-duplicate removal improves perplexity, reduces memorization, and mitigates benchmark contamination. SemDeDup (Abbas et al. 2023) extended to embedding-space near-duplicates. MinHash-LSH is now standard; FineWeb's ablations show per-dump deduplication outperforms global deduplication — a counterintuitive result that reopened assumptions.

**Model-based quality filtering.** The turning point is **DCLM** (DataComp for Language Models; Li et al., June 2024). Using a 240T-token Common Crawl pool and a fixed training recipe, DCLM isolated data curation as the independent variable. The winning recipe — a fastText classifier trained to distinguish OpenHermes-2.5+ELI5-style instruction data from random web — produced **DCLM-Baseline**, which trains a 7B model to 64% MMLU on 2.6T tokens, a 6.6-point jump over MAP-Neo at 40% less compute. Parallel and complementary: **FineWeb-Edu** (Penedo et al., HuggingFace, June 2024) uses a Llama-3-70B-annotated educational-quality classifier (Snowflake Arctic regressor, F1 0.82 at threshold 3) to cut FineWeb from 15T to 1.3T "educational" tokens, with large MMLU/ARC/OpenBookQA gains at 1.8B/350B-token ablation scale. **Dolma** (AI2 2024; 3T open tokens) and **Nemotron-CC** (NVIDIA 2024, ~6.3T tokens with multi-classifier ensembling) are the documented industrial recipes. **Zyda** (Zyphra 2024) and **SmolLM-Corpus/SmolLM2** data mixes (HuggingFace 2024–2025) extend these ideas to smaller compute budgets.

**Contamination control.** Detection of benchmark leakage (MMLU, GSM8K, HumanEval in pretraining) became a first-class concern after reports that several 2023 "SOTA" models had memorized test questions. LLaMA, FineWeb, DCLM, and Dolma all publish decontamination audits; DCLM notably showed removing MMLU-overlap samples from its baseline *did not* drop MMLU accuracy, meaning the gains were real, not contamination.

**Mixing and domain weighting.** **DoReMi** (Xie et al. 2023) learns domain mixture weights via group-DRO on a proxy model; **Data Mixing Laws** (Ye et al. 2024) fit predictable scaling curves. These are real but second-order effects compared to filtering.

**Bottom line:** quality filtering is the most reproducible data lever of 2023–2025, with per-paper MMLU gains of 3–7 points at matched compute. The ceiling is real — you cannot filter your way to a capability not present in the raw data — but most labs are still below it.