---
id: diversity-coverage-expansion
name: Diversity and Coverage Expansion
description: Multilingual, multimodal, and long-tail corpora that expand the envelope
  of what models can serve.
origin: bootstrap
novelty_status: globally_novel
key_entity_ids:
- roots-bloom
- nllb
- madlad-400
- aya
- fineweb-2
- laion-5b
- obelics
- datacomp
- coyo-700m
created_at: '2026-04-25'
updated_at: '2026-04-25'
---
Multilingual and multimodal coverage has advanced through several coordinated efforts. **CC-100** and **mC4** provided early multilingual baselines. **BLOOM's ROOTS corpus** (BigScience 2022, 1.6TB across 46 languages) was the first serious open multilingual LLM corpus. **NLLB-200** (Meta 2022) extended machine translation to 200 languages. **MADLAD-400** (Google 2023, 3T tokens across 419 languages) and **Aya Collection** (Cohere for AI 2024, 513M instances across 114 languages, 204K human-curated) pushed further. **FineWeb-2** (Dec 2024, 20TB across 1,868 language-script pairs, 96 CC snapshots) is the current open frontier and beats CC-100/mC4/CulturaX/HPLT on nine-language ablations.

Multimodal: **CLIP's WIT** (proprietary, 400M pairs), then the LAION series, then **COYO-700M** (Kakao 2022), **DataComp-1B** (2023, DataComp benchmark for image-text curation), **OBELICS** (HuggingFace 2023, 141M interleaved web docs enabling IDEFICS), and **MMC4** / **WebLI** (Google PaLI). For video: WebVid-10M's takedown after the Shutterstock lawsuit is a cautionary tale, and open video pretraining now relies on Panda-70M, OpenVid-1M, and licensed deals.

**Long-tail and low-resource work** — Masakhane (African languages), AmericasNLP (Indigenous), XTREME-R, MEGA multilingual benchmarks — remains undersupplied. The pattern: scaling laws look unfavorable for languages with <1B tokens on the web, so the field has increasingly used cross-lingual transfer and LLM-translated synthetic data rather than collecting more real data.