# Emerging Data Advantages in AI

**The durable advantages in modern AI sit in data, not architectures.** Since AlexNet, nearly every regime-shifting capability — supervised vision, LLM pretraining, open diffusion, code copilots, protein structure, and now reasoning — has been unlocked by a dataset or data pipeline more than by a model. The moat has migrated over time: from scale (ImageNet, Common Crawl), to filtering (C4→FineWeb→DCLM), to preferences (InstructGPT, Anthropic HH, UltraFeedback), to synthetic distillation (Phi, DeepSeek-R1 traces), and increasingly to legal and licensing access (Bartz v. Anthropic, NYT v. OpenAI, Reddit deals). Architectures, by contrast, have converged: transformer decoders and diffusion UNets are commodity. What follows tracks the recurring patterns, names the specific contributions that matter, anchors them on a dated timeline, and flags where the evidence is thin.

A few cross-cutting facts worth stating upfront. First, data-quality ablations now routinely beat 2× compute: FineWeb-Edu's classifier filter and DCLM-Baseline's fastText model-based filtering each move MMLU by 4–7 points at fixed compute versus prior open corpora. Second, pure synthetic pretraining has not demonstrated a clean scaling story beyond ~14B parameters; the Phi evaluations remain contested, while reasoning distillation (R1-style SFT on CoT traces) is the one synthetic recipe with uncontested transfer. Third, robotics, math, and biology each illustrate the same pattern — a single well-structured corpus (DROID, MATH, PDB) unlocks what architecture alone could not. Fourth, the legal frontier in 2025 (Bartz, Kadrey summary judgments) tentatively blesses training on lawfully-acquired copyrighted text as fair use while penalizing piracy-sourced corpora; this is quietly reshaping who can train what.

## Conclusion: What has actually changed

Across 2012–2026, data advantages moved through four generations. Raw scale (ImageNet, Common Crawl) gave way to smart filtering (C4, FineWeb, DCLM) as the web saturated. Filtering gave way to elicitation — RLHF and DPO on preference data that extracts capability the pretraining already latent. Elicitation is now giving way to **synthesized supervision**: reasoning traces, verifier-checked math solutions, and distilled teacher outputs that effectively transfer compute from a large model into the training signal for a smaller one.

The honest read for a builder in 2026: the highest-ROI data work is probably **not** collecting more tokens. It is (1) running DCLM-style filtering ablations on whatever pretraining you do, (2) investing in a domain-specific verifier and an R1-style distillation loop where verifiers exist, (3) using ~50K high-quality preference pairs with DPO rather than scaled low-quality feedback, and (4) auditing your legal exposure on data provenance, especially anything sourced from shadow libraries. The overhyped items: Phi-style textbook-only pretraining at scale, unverified synthetic pretraining at >30% of the mix, and any claim that data collapse from synthetic content is imminent for labs that accumulate rather than replace real data. The underhyped: robotics data collection (still hardware-bound, still the bottleneck) and licensed-data deals as a medium-term structural moat.

---

## Theme: scale-unlocking-corpora

The deep-learning era begins not with AlexNet but with **ImageNet** (Deng et al. 2009; ILSVRC benchmark 2010–2017). Fei-Fei Li's insistence that the bottleneck was data, not models, turned out to be correct: Krizhevsky, Sutskever, and Hinton's 2012 AlexNet win on ILSVRC-2012 (top-5 error 15.3% vs. 26.2%) was a model paper, but the enabling artifact was the 1.2M labeled training images. Every supervised-vision result for the next five years (VGG, ResNet, Inception, DenseNet) was an ImageNet-pretrained model. **Transfer learning as a paradigm is downstream of a single dataset.**

For text, **Common Crawl** (non-profit web crawl founded 2007, ~250B pages to date) is the substrate. GPT-2's **WebText** (Radford et al. 2019) filtered CC by outbound-Reddit karma; GPT-3 (Brown et al. 2020) trained on ~570GB of filtered CC plus Books, Wikipedia, and WebText2 — roughly 300B tokens total, the first demonstration that in-context learning emerges at scale. **The Pile** (Gao et al., EleutherAI 2020) — 825GB across 22 curated sources (PubMed, ArXiv, GitHub, Books3, Stack Exchange, etc.) — was the open answer and powered every non-proprietary LLM from GPT-J to Pythia. **C4** (Colossal Clean Crawled Corpus; Raffel et al. 2019 as part of T5) and its mC4 multilingual variant established the basic web-cleaning recipe (langID, boilerplate removal, bad-word filters) still used today. **RefinedWeb** (Penedo et al., TII 2023) showed for the first time that heavy deduplication plus aggressive filtering on web-only data matches curated mixes — Falcon-40B trained on RefinedWeb reached near-LLaMA performance without books or code. **RedPajama-v1** (Together AI 2023) open-reproduced LLaMA's 1.2T-token mix; **RedPajama-v2** (2023) scaled to 30T tokens of CC with quality signals.

For image-text, **LAION-400M** (Schuhmann et al. 2021) and **LAION-5B** (2022) — open CLIP-filtered image-URL-caption pairs — were the direct precondition for Stable Diffusion 1.x. They remain the clearest case of an open dataset producing an entire generative-model ecosystem. For video, **HowTo100M** (2019), **WebVid-10M** (2021, since withdrawn over licensing), **Panda-70M** (2024), and **OpenVid-1M** (2024) have played analogous but weaker roles — video pretraining data is still the bottleneck, not modeling, in text-to-video.

**What the evidence says in 2026:** the "scale unlocks capabilities" story holds for pretraining regime shifts (supervised vision → self-supervised language → multimodal → reasoning), but the incremental gain from adding raw web tokens beyond ~15T has flattened. This is why the action moved to filtering.

## Theme: quality-filtering-curation

Between 2021 and 2024, the field discovered that **most web tokens are noise, and intelligent removal beats addition.** Four pillars.

**Deduplication.** Lee et al. (2021), "Deduplicating Training Data Makes Language Models Better," showed exact and near-duplicate removal improves perplexity, reduces memorization, and mitigates benchmark contamination. SemDeDup (Abbas et al. 2023) extended to embedding-space near-duplicates. MinHash-LSH is now standard; FineWeb's ablations show per-dump deduplication outperforms global deduplication — a counterintuitive result that reopened assumptions.

**Model-based quality filtering.** The turning point is **DCLM** (DataComp for Language Models; Li et al., June 2024). Using a 240T-token Common Crawl pool and a fixed training recipe, DCLM isolated data curation as the independent variable. The winning recipe — a fastText classifier trained to distinguish OpenHermes-2.5+ELI5-style instruction data from random web — produced **DCLM-Baseline**, which trains a 7B model to 64% MMLU on 2.6T tokens, a 6.6-point jump over MAP-Neo at 40% less compute. Parallel and complementary: **FineWeb-Edu** (Penedo et al., HuggingFace, June 2024) uses a Llama-3-70B-annotated educational-quality classifier (Snowflake Arctic regressor, F1 0.82 at threshold 3) to cut FineWeb from 15T to 1.3T "educational" tokens, with large MMLU/ARC/OpenBookQA gains at 1.8B/350B-token ablation scale. **Dolma** (AI2 2024; 3T open tokens) and **Nemotron-CC** (NVIDIA 2024, ~6.3T tokens with multi-classifier ensembling) are the documented industrial recipes. **Zyda** (Zyphra 2024) and **SmolLM-Corpus/SmolLM2** data mixes (HuggingFace 2024–2025) extend these ideas to smaller compute budgets.

**Contamination control.** Detection of benchmark leakage (MMLU, GSM8K, HumanEval in pretraining) became a first-class concern after reports that several 2023 "SOTA" models had memorized test questions. LLaMA, FineWeb, DCLM, and Dolma all publish decontamination audits; DCLM notably showed removing MMLU-overlap samples from its baseline *did not* drop MMLU accuracy, meaning the gains were real, not contamination.

**Mixing and domain weighting.** **DoReMi** (Xie et al. 2023) learns domain mixture weights via group-DRO on a proxy model; **Data Mixing Laws** (Ye et al. 2024) fit predictable scaling curves. These are real but second-order effects compared to filtering.

**Bottom line:** quality filtering is the most reproducible data lever of 2023–2025, with per-paper MMLU gains of 3–7 points at matched compute. The ceiling is real — you cannot filter your way to a capability not present in the raw data — but most labs are still below it.

## Theme: synthetic-data-generation

Synthetic data has three genuinely different regimes, which are too often lumped together.

**Instruction distillation** — generate prompt/response pairs from a stronger model, fine-tune a weaker one. **Self-Instruct** (Wang et al., Dec 2022) bootstrapped 52K instructions from a seed model; **Alpaca** (Taori et al., Stanford, March 2023) applied it via text-davinci-003, and **Vicuna / ShareGPT** (LMSYS, March 2023) used scraped ChatGPT conversations. Alpaca cost $600 and spawned the open-instruction ecosystem. **WizardLM / Evol-Instruct** (Xu et al. 2023) iteratively complexified prompts; **Orca / Orca 2** (Mukherjee et al., Microsoft 2023) added GPT-4 explanation traces. These methods **reliably transfer instruction-following style and some task performance but do not transfer deep capabilities the teacher had from pretraining.**

**Textbook-style pretraining synthesis.** The **Phi series** (Gunasekar et al., "Textbooks Are All You Need," June 2023; through Phi-4, Dec 2024) argues that GPT-generated textbook-like pretraining data can produce small models punching well above their weight. Phi-3 (3.8B) and Phi-4 (14B) score competitively on MMLU and HumanEval at their scale. **This is the most contested line of work in data-centric AI.** Independent reproductions (TinyLlama, OpenPhi attempts) have not matched the reported numbers, and Phi's benchmark dominance doesn't consistently transfer to LMSYS Arena or harder reasoning benchmarks, raising concerns about benchmark-targeted synthesis. **Cosmopedia** (HuggingFace 2024, 25B synthetic tokens) and **WRAP / Rephrasing the Web** (Maini et al. 2024) are open implementations. Net: useful as a mixing ingredient at 10–30% of pretraining, not as a substitute.

**Reasoning-trace distillation.** This is the one synthetic regime with unambiguous, reproducible gains. **STaR** (Zelikman et al. 2022) pioneered generating chains-of-thought, filtering by answer correctness, and fine-tuning on the filtered set. **OpenAI o1** (Sept 2024) scaled this to RL on long CoTs, though training data remains closed. **DeepSeek-R1** (Jan 2025; Nature paper Sept 2025) made the recipe explicit: R1-Zero applies pure RL to DeepSeek-V3-Base with verifiable-reward tasks (math, code), producing emergent long CoT; R1 adds cold-start SFT; and **R1-distilled models** fine-tune Qwen/Llama bases on 800K curated R1 traces. Distilled DeepSeek-R1-Qwen-32B hit 72.6% AIME 2024 and 94.3% MATH-500, previously thought to require frontier-scale RL. The open community replicated the recipe within months: **OpenThoughts / OpenThinker3-7B** (June 2025, 1.2M traces from QwQ-32B, 53% AIME 2025), **Bespoke-Stratos**, **Sky-T1**, **AM-DeepSeek-R1-Distilled-1.4M**, and **NuminaMath-CoT**. Reasoning distillation now costs under $1K for 7B models and is arguably the largest shift in training economics since instruction tuning.

**The model-collapse debate.** Shumailov et al.'s Nature 2024 paper ("AI models collapse when trained on recursively generated data") demonstrated degeneration under recursive self-training. **Gerstgrasser et al. (2024), "Is Model Collapse Inevitable?", showed that if synthetic data is *accumulated* alongside real data rather than replacing it, collapse does not occur — which is what frontier labs actually do.** Collapse is a real risk for naive pipelines but not a ceiling on synthetic methods with grounded verifiers (math answer-checking, code execution, preference labels).

## Theme: domain-specific-unlocks

**Code.** GitHub scrapes enabled **Codex** (OpenAI 2021) and its product Copilot — the first data-driven product moat from training corpus access. **The Stack** (BigCode/HuggingFace 2022, 6TB permissively licensed) and **The Stack v2** (Feb 2024, 900B tokens, paired with Software Heritage archive) replaced opaque scrapes with documented, license-filtered code. StarCoder and StarCoder2 trained on them; DeepSeek-Coder, Qwen-Coder, and Code Llama use closely related mixes. **HumanEval** (Chen et al. 2021) and **MBPP** became the universal code benchmarks; **SWE-bench** (Jimenez et al. 2023) shifted the goalposts toward real repo-level tasks.

**Math and reasoning.** **GSM8K** (Cobbe et al., OpenAI 2021; 8.5K grade-school problems) and **MATH** (Hendrycks et al. 2021; 12.5K competition problems) defined the evaluation ladder. **PRM800K** (Lightman et al. 2023) introduced step-level process reward labels and validated process-reward models. **OpenWebMath** (Paster et al. 2023, 14.7B tokens), **MetaMathQA**, **OpenMathInstruct** (NVIDIA 2024, 1.8M problem-solution pairs), and **NuminaMath** (2024, AIMO winner) scaled training corpora. The current frontier is formal math: **MiniF2F**, **ProofNet**, and **Lean-Mathlib** as training+eval targets for AlphaProof-style systems.

**Robotics.** Robot manipulation data is the single biggest bottleneck in modern AI. **Ego4D** (Meta 2021, 3,670 hours egocentric video) provided observational grounding. **RT-1** (Google 2022, 130K episodes on Everyday Robots) established scale collection. **Open X-Embodiment / RT-X** (Oct 2023, 22 embodiments, ~1M trajectories from 34 labs) was the first cross-institution consortium dataset and the precondition for RT-2-X's positive transfer across embodiments. **DROID** (Khazatsky et al., RSS 2024) is the current reference: **76K teleoperated trajectories, 350 hours, 564 scenes, 86 tasks, 13 institutions, all on a standardized Franka Panda platform**, released CC-BY-4.0. Octo and Pi-0 (Physical Intelligence 2024) are DROID/OXE-trained generalist policies. Robotics remains a domain where **hardware-standardized, teleoperation-collected data is non-substitutable by synthetic or video** — a rare counterexample to the scraping-plus-synthesis default.

**Biology.** The **Protein Data Bank** (PDB, RCSB, founded 1971; ~220K structures) is the foundational corpus; **AlphaFold 2** (Jumper et al., Nature 2021) used PDB plus UniRef/BFD multiple-sequence alignments to solve protein structure prediction at near-experimental accuracy, the clearest single case of a decades-old curated dataset enabling a regime change once paired with the right model. **AlphaFold 3** (May 2024) extended to complexes with nucleic acids and ligands. **ESM-2 / ESM-3** (Meta/EvolutionaryScale) pretrain on UniRef-50/90 at scale; **GNoME** (DeepMind 2023) discovered 2.2M new crystals from Materials Project-scale data.

**Vision-dense annotation.** **MS COCO** (Lin et al. 2014, 330K images, 2.5M object instances, 5 captions each) defined detection/segmentation/captioning for a decade. **Visual Genome** (Krishna et al. 2016), **ADE20K**, **Cityscapes**, **LVIS** filled niches. **Segment Anything / SA-1B** (Kirillov et al., Meta 2023) — **11M images, 1.1B masks, the largest segmentation dataset by ~400×** — was generated through a model-in-the-loop annotation flywheel and enabled zero-shot segmentation as a primitive.

## Theme: human-preference-alignment

Preference data is where explicit human labor meets the model — and therefore where budgets, IP, and demonstrable quality still differentiate labs.

**InstructGPT** (Ouyang et al., OpenAI Jan 2022) established the SFT→RM→PPO pipeline; the exact prompts and demonstrations remain proprietary. **Anthropic HH-RLHF** (Bai et al., April 2022, ~170K human preference comparisons for helpfulness and harmlessness) is the canonical open preference dataset. **Constitutional AI / RLAIF** (Bai et al., Dec 2022) showed model-written critiques can substitute for human red-team labels on harmlessness, with comparable results — the first evidence that AI feedback scales for alignment, foreshadowing UltraFeedback.

**OpenAssistant / OASST1-OASST2** (LAION, April 2023, ~161K messages across 66K conversation trees) was the community-sourced open analog. **UltraFeedback** (Cui et al., Oct 2023, 64K prompts × 4 responses × GPT-4 scores on four axes) became the default DPO dataset after **Zephyr-7B** (HuggingFace, Oct 2023) showed UltraFeedback+DPO beat RLHF baselines on MT-Bench. **DPO** itself (Rafailov et al., May 2023) collapsed the RM+PPO pipeline into a single contrastive loss and reshaped the economics — small teams can now align with ~10K preference pairs and a few GPU-hours.

**NVIDIA HelpSteer / HelpSteer2** (2023–2024) and **Nectar** (2023) extend multi-attribute labeling. **Tulu 2 / Tulu 3** (AI2, 2023–2024) are the most thoroughly documented open post-training pipelines, with Tulu 3's RLVR (RL with verifiable rewards) anticipating R1. **RewardBench** (Lambert et al., March 2024) finally provided a standardized evaluation for reward models, revealing that many open RMs are barely better than length-counting.

**Open debates:** Is DPO equivalent to PPO? (Evidence suggests yes on capability, no on robustness to distribution shift.) Does GPT-4-labeled preference data suffer from stylistic bias (length, formatting) that length-controls remove? (Yes, clearly.) Is there a preference-data-scaling law analogous to pretraining? (Unclear — gains saturate faster, and quality dominates quantity past ~50K pairs.)

## Theme: diversity-coverage-expansion

Multilingual and multimodal coverage has advanced through several coordinated efforts. **CC-100** and **mC4** provided early multilingual baselines. **BLOOM's ROOTS corpus** (BigScience 2022, 1.6TB across 46 languages) was the first serious open multilingual LLM corpus. **NLLB-200** (Meta 2022) extended machine translation to 200 languages. **MADLAD-400** (Google 2023, 3T tokens across 419 languages) and **Aya Collection** (Cohere for AI 2024, 513M instances across 114 languages, 204K human-curated) pushed further. **FineWeb-2** (Dec 2024, 20TB across 1,868 language-script pairs, 96 CC snapshots) is the current open frontier and beats CC-100/mC4/CulturaX/HPLT on nine-language ablations.

Multimodal: **CLIP's WIT** (proprietary, 400M pairs), then the LAION series, then **COYO-700M** (Kakao 2022), **DataComp-1B** (2023, DataComp benchmark for image-text curation), **OBELICS** (HuggingFace 2023, 141M interleaved web docs enabling IDEFICS), and **MMC4** / **WebLI** (Google PaLI). For video: WebVid-10M's takedown after the Shutterstock lawsuit is a cautionary tale, and open video pretraining now relies on Panda-70M, OpenVid-1M, and licensed deals.

**Long-tail and low-resource work** — Masakhane (African languages), AmericasNLP (Indigenous), XTREME-R, MEGA multilingual benchmarks — remains undersupplied. The pattern: scaling laws look unfavorable for languages with <1B tokens on the web, so the field has increasingly used cross-lingual transfer and LLM-translated synthetic data rather than collecting more real data.

## Theme: annotation-dense-datasets

The unifying thread here is that **structured supervision encodes a prior that self-supervision cannot reach efficiently.** ImageNet (class labels), COCO (boxes, masks, captions), Visual Genome (scene graphs), RefCOCO (grounding phrases), Kinetics (action), AudioSet (audio-event labels): each added one annotation type and enabled a sub-field.

SA-1B's 1.1B masks exemplify the modern version — **dense annotation via a model-in-the-loop flywheel**, where an initial model assists human annotators, its outputs are corrected, and the improved model assists the next round. This cut per-mask cost by ~100× and produced a foundation-model-quality training set in ~12 months. The same pattern now appears in **OpenThoughts** (R1 generates traces, humans/filters curate) and in robotics (DROID scripts randomized scene perturbations during teleoperation).

Chain-of-thought annotations in datasets like **ScienceQA**, **MathInstruct**, and **BIG-Bench Hard** can be seen as annotation-dense math/reasoning corpora. The frontier question: how much of the value is the reasoning steps themselves versus the final answer plus a good verifier?

## Theme: provenance-and-licensing

The competitive landscape of 2024–2026 is substantially shaped by legal and access shifts.

**Landmark rulings.** In **Bartz v. Anthropic** (N.D. Cal., Judge Alsup, June 23, 2025), training Claude on copyrighted books was ruled "quintessentially transformative" fair use — but downloading ~7M books from shadow libraries (LibGen, PiLiMi) was not. Class certification (482K works × up to $150K statutory damages) produced a reported settlement in Sept 2025. Two days later, **Kadrey v. Meta** (Judge Chhabria, June 25, 2025) reached a similar fair-use conclusion on training, but with more weight on market-harm evidence. These are district-court rulings, not appellate, and **they bless training while penalizing pirated sourcing** — meaning labs' legitimately-licensed data paths now matter for liability, not just PR.

**NYT v. OpenAI/Microsoft** (filed Dec 2023, motion to dismiss largely denied March/April 2025, proceeding to trial): the most consequential AI copyright case, complicated by a May 2025 preservation order forcing OpenAI to retain all user ChatGPT logs (over objections on privacy grounds, affirmed June 2025). A broader wave of suits (Authors Guild, Silverman, Getty Images v. Stability AI in UK and US, music publishers v. Anthropic) remains unresolved.

**LAION-5B CSAM incident.** Stanford Internet Observatory's Dec 2023 report found 1,008 suspected-CSAM URLs in LAION-5B. LAION pulled the dataset; Runway subsequently withdrew Stable Diffusion 1.5 from HuggingFace. **Re-LAION-5B** (Aug 2024) removed 2,236 links in partnership with IWF, C3P, and Stanford, and restored distribution. This is now the industry reference incident for web-scrape hygiene.

**Licensing deals as moat.** OpenAI has signed with AP, Axel Springer, FT, News Corp, Le Monde, Reddit, Stack Overflow, Shutterstock; Google with Reddit (~$60M/yr). These are increasingly exclusive and forward-licensed — meaning future open/smaller-lab models lose access to the same corpora. **The Data Provenance Initiative** (Longpre et al., 2023–2024; "Consent in Crisis" 2024) audited licenses on 1,800+ datasets and documented rapid closure: the share of web tokens behind robots.txt opt-outs for AI crawlers rose from ~1% to ~25% in a year for top domains.

**Open-licensed counter-efforts.** **Common Pile** (EleutherAI 2024–2025) and **KL3M** assemble public-domain and permissively-licensed corpora. Early ablations suggest open-licensed-only models can reach ~80% of mixed-corpus performance at the 7B scale — useful but not parity. **C2PA content credentials** and dataset cards/datasheets (Gebru et al., Mitchell et al.) remain the documentation substrate.

**Practical implication:** the durable data moat for frontier labs in 2026 is a combination of (a) licensed proprietary text/image/video deals, (b) user-conversation data from deployed products, and (c) in-house preference and reasoning-trace pipelines. For open-weight labs, it is (a) FineWeb/DCLM-scale filtered public corpora and (b) R1-style distillation from the largest open teacher. These bifurcate further each quarter.

```json
{
  "themes": [
    {
      "id": "scale-unlocking-corpora",
      "name": "Scale-Unlocking Corpora",
      "description": "Datasets whose size and coverage enabled new capability regimes once paired with the right model.",
      "taxonomy_ref": null,
      "key_entity_ids": ["imagenet", "common-crawl", "the-pile", "c4", "laion-5b", "refinedweb", "gpt-3", "alexnet"]
    },
    {
      "id": "quality-filtering-curation",
      "name": "Quality Filtering and Curation",
      "description": "Advances in deduplication, classifier-based filtering, contamination control, and data mixing that extract more capability per token.",
      "taxonomy_ref": null,
      "key_entity_ids": ["c4", "refinedweb", "fineweb", "fineweb-edu", "dclm", "dolma", "redpajama", "nemotron-cc", "doremi"]
    },
    {
      "id": "synthetic-data-generation",
      "name": "Synthetic Data Generation",
      "description": "Model-generated training data for distillation, instruction tuning, textbook-style pretraining, and reasoning-trace transfer.",
      "taxonomy_ref": null,
      "key_entity_ids": ["self-instruct", "alpaca", "sharegpt", "phi", "orca", "cosmopedia", "deepseek-r1", "openai-o1", "openthoughts", "star-method", "shumailov-collapse"]
    },
    {
      "id": "domain-specific-unlocks",
      "name": "Domain-Specific Unlocks",
      "description": "Datasets that unlocked strong performance in code, math, robotics, and biology by providing structured supervision unavailable from the web.",
      "taxonomy_ref": null,
      "key_entity_ids": ["the-stack", "humaneval", "gsm8k", "math-dataset", "prm800k", "open-x-embodiment", "droid", "ego4d", "pdb", "alphafold", "sam-sa1b"]
    },
    {
      "id": "human-preference-alignment",
      "name": "Human-Preference and Alignment Data",
      "description": "Preference datasets for RLHF, DPO, and constitutional-style training that elicit capability and shape behavior.",
      "taxonomy_ref": null,
      "key_entity_ids": ["instructgpt", "anthropic-hh", "constitutional-ai", "openassistant", "ultrafeedback", "dpo", "tulu", "helpsteer", "rewardbench", "prm800k"]
    },
    {
      "id": "diversity-coverage-expansion",
      "name": "Diversity and Coverage Expansion",
      "description": "Multilingual, multimodal, and long-tail corpora that expand the envelope of what models can serve.",
      "taxonomy_ref": null,
      "key_entity_ids": ["roots-bloom", "nllb", "madlad-400", "aya", "fineweb-2", "laion-5b", "obelics", "datacomp", "coyo-700m"]
    },
    {
      "id": "annotation-dense-datasets",
      "name": "Annotation-Dense Datasets",
      "description": "Datasets with rich structured supervision (boxes, masks, captions, scene graphs, reasoning traces) that encode priors self-supervision cannot reach efficiently.",
      "taxonomy_ref": null,
      "key_entity_ids": ["coco", "visual-genome", "sam-sa1b", "open-x-embodiment", "droid", "prm800k", "openthoughts"]
    },
    {
      "id": "provenance-and-licensing",
      "name": "Provenance, Licensing, and the Legal Moat",
      "description": "Copyright rulings, licensing deals, opt-outs, and dataset audits that reshape which data is practically and legally usable.",
      "taxonomy_ref": null,
      "key_entity_ids": ["bartz-v-anthropic", "kadrey-v-meta", "nyt-v-openai", "re-laion-5b", "data-provenance-initiative", "common-pile", "openai", "getty-v-stability"]
    }
  ],
  "entities": [
    {"id": "imagenet", "name": "ImageNet", "entity_type": "dataset", "description": "1.2M+ labeled images across 1,000 classes (Deng et al. 2009); catalyzed AlexNet (2012) and the supervised-vision era."},
    {"id": "alexnet", "name": "AlexNet", "entity_type": "method", "description": "2012 ILSVRC-winning CNN (Krizhevsky, Sutskever, Hinton) whose result depended fundamentally on ImageNet scale."},
    {"id": "common-crawl", "name": "Common Crawl", "entity_type": "dataset", "description": "Open web crawl corpus, founded 2007, underlying nearly every open LLM pretraining mix."},
    {"id": "gpt-3", "name": "GPT-3", "entity_type": "product", "description": "OpenAI 2020 model trained on ~300B filtered tokens; demonstrated in-context learning at scale."},
    {"id": "the-pile", "name": "The Pile", "entity_type": "dataset", "description": "EleutherAI's 825GB open corpus (Gao et al. 2020) across 22 curated sources; substrate for GPT-J, Pythia, and most early open LLMs."},
    {"id": "c4", "name": "C4 (Colossal Clean Crawled Corpus)", "entity_type": "dataset", "description": "Raffel et al. 2019/2020 cleaned Common Crawl dump from the T5 paper; established the standard web-filtering recipe."},
    {"id": "refinedweb", "name": "RefinedWeb", "entity_type": "dataset", "description": "Penedo et al. 2023 (TII/Falcon); demonstrated heavy dedup + aggressive filtering on web-only matches curated mixes."},
    {"id": "redpajama", "name": "RedPajama", "entity_type": "dataset", "description": "Together AI 2023 open reproduction of LLaMA's 1.2T-token mix; v2 (30T CC tokens with quality signals) followed."},
    {"id": "fineweb", "name": "FineWeb", "entity_type": "dataset", "description": "HuggingFace 2024 15T-token filtered CC corpus with fully documented pipeline and extensive ablations."},
    {"id": "fineweb-edu", "name": "FineWeb-Edu", "entity_type": "dataset", "description": "Llama-3-annotated educational classifier filter reducing FineWeb to 1.3T high-quality tokens with large MMLU/ARC gains."},
    {"id": "fineweb-2", "name": "FineWeb-2", "entity_type": "dataset", "description": "HuggingFace Dec 2024 multilingual extension: 20TB across 1,868 language-script pairs, beats CC-100/mC4/CulturaX on 9-language ablations."},
    {"id": "dolma", "name": "Dolma", "entity_type": "dataset", "description": "AI2's 3T-token open corpus (2024) with fully documented pipeline; powers OLMo."},
    {"id": "dclm", "name": "DCLM (DataComp for Language Models)", "entity_type": "benchmark", "description": "Li et al. 2024 testbed with 240T CC pool and fixed training recipe; DCLM-Baseline reaches 64% MMLU at 7B/2.6T."},
    {"id": "nemotron-cc", "name": "Nemotron-CC", "entity_type": "dataset", "description": "NVIDIA 2024 ~6.3T-token CC pipeline using multi-classifier ensemble filtering."},
    {"id": "doremi", "name": "DoReMi", "entity_type": "method", "description": "Xie et al. 2023 group-DRO method for learning domain mixture weights via a proxy model."},
    {"id": "laion-5b", "name": "LAION-5B", "entity_type": "dataset", "description": "Schuhmann et al. 2022 open CLIP-filtered image-text pair dataset (5.85B pairs); precondition for Stable Diffusion."},
    {"id": "coyo-700m", "name": "COYO-700M", "entity_type": "dataset", "description": "Kakao 2022 open 700M image-text pairs; alternative/complement to LAION."},
    {"id": "datacomp", "name": "DataComp", "entity_type": "benchmark", "description": "Gadre et al. 2023 benchmark for image-text curation with fixed CLIP training recipe; analog of DCLM for multimodal."},
    {"id": "obelics", "name": "OBELICS", "entity_type": "dataset", "description": "HuggingFace 2023 open interleaved image-text web documents (141M) enabling IDEFICS and open multimodal models."},
    {"id": "self-instruct", "name": "Self-Instruct", "entity_type": "method", "description": "Wang et al. Dec 2022 pipeline bootstrapping 52K instructions from a seed LM; foundational for distilled instruction tuning."},
    {"id": "alpaca", "name": "Alpaca", "entity_type": "dataset", "description": "Stanford March 2023 52K instruction dataset generated from text-davinci-003 at ~$600 cost."},
    {"id": "sharegpt", "name": "ShareGPT / Vicuna", "entity_type": "dataset", "description": "User-shared ChatGPT conversations (2023) used to train LMSYS's Vicuna; popularized distilled chat tuning."},
    {"id": "phi", "name": "Phi series", "entity_type": "product", "description": "Microsoft's small models (Phi-1 through Phi-4, 2023–2024) trained heavily on synthetic textbook-style data; results strong on benchmarks, contested on Arena-style evaluation."},
    {"id": "orca", "name": "Orca / Orca 2", "entity_type": "dataset", "description": "Microsoft 2023 distilled datasets using GPT-4 explanation traces on FLAN collections."},
    {"id": "cosmopedia", "name": "Cosmopedia", "entity_type": "dataset", "description": "HuggingFace 2024 open 25B-token synthetic textbook-style corpus; open analog of Phi's data."},
    {"id": "star-method", "name": "STaR", "entity_type": "method", "description": "Zelikman et al. 2022 Self-Taught Reasoner; generate CoT, filter by correct answer, fine-tune; foundational for reasoning distillation."},
    {"id": "deepseek-r1", "name": "DeepSeek-R1", "entity_type": "product", "description": "DeepSeek Jan 2025 reasoning model; R1-Zero uses pure RL with verifiable rewards, R1 adds SFT, R1-distilled fine-tunes Qwen/Llama on 800K traces."},
    {"id": "openai-o1", "name": "OpenAI o1", "entity_type": "product", "description": "OpenAI Sept 2024 reasoning model using RL over long CoTs; training data and recipe remain closed."},
    {"id": "openthoughts", "name": "OpenThoughts / OpenThinker", "entity_type": "dataset", "description": "Open 2025 reasoning-trace corpus (OpenThoughts3: 1.2M QwQ-32B traces) enabling open R1-parity distilled models."},
    {"id": "shumailov-collapse", "name": "Shumailov et al. model collapse", "entity_type": "method", "description": "Nature 2024 paper showing recursive training on self-generated data degrades models; Gerstgrasser et al. 2024 showed accumulation (not replacement) avoids collapse."},
    {"id": "instructgpt", "name": "InstructGPT", "entity_type": "method", "description": "Ouyang et al. OpenAI 2022; established SFT→RM→PPO RLHF pipeline."},
    {"id": "anthropic-hh", "name": "Anthropic HH-RLHF", "entity_type": "dataset", "description": "Bai et al. April 2022; ~170K human preference pairs on helpfulness and harmlessness; canonical open RLHF dataset."},
    {"id": "constitutional-ai", "name": "Constitutional AI / RLAIF", "entity_type": "method", "description": "Anthropic Dec 2022; model-written critiques substitute for human harmlessness labels — first scaled AI-feedback result."},
    {"id": "openassistant", "name": "OpenAssistant / OASST", "entity_type": "dataset", "description": "LAION April 2023; 161K community-sourced messages across 66K conversation trees."},
    {"id": "ultrafeedback", "name": "UltraFeedback", "entity_type": "dataset", "description": "Cui et al. Oct 2023; 64K prompts × 4 responses × GPT-4 multi-attribute scoring; default DPO corpus."},
    {"id": "dpo", "name": "DPO (Direct Preference Optimization)", "entity_type": "method", "description": "Rafailov et al. May 2023; single-loss alternative to PPO that collapsed the RLHF pipeline and reshaped post-training economics."},
    {"id": "helpsteer", "name": "HelpSteer / HelpSteer2", "entity_type": "dataset", "description": "NVIDIA 2023–2024 multi-attribute preference datasets."},
    {"id": "tulu", "name": "Tulu 2/3", "entity_type": "dataset", "description": "AI2 2023–2024 fully documented open post-training datasets; Tulu 3 introduced RLVR (RL with verifiable rewards)."},
    {"id": "rewardbench", "name": "RewardBench", "entity_type": "benchmark", "description": "Lambert et al. March 2024; standardized reward-model evaluation; exposed length-bias in many open RMs."},
    {"id": "prm800k", "name": "PRM800K", "entity_type": "dataset", "description": "Lightman et al. 2023 OpenAI; 800K step-level process-reward labels on MATH problems."},
    {"id": "the-stack", "name": "The Stack (v1/v2)", "entity_type": "dataset", "description": "BigCode/HuggingFace 2022 and 2024; permissively-licensed code corpus (v2: 900B tokens) underlying StarCoder."},
    {"id": "humaneval", "name": "HumanEval", "entity_type": "benchmark", "description": "Chen et al. 2021 OpenAI; 164 Python programming problems; universal code benchmark."},
    {"id": "gsm8k", "name": "GSM8K", "entity_type": "benchmark", "description": "Cobbe et al. OpenAI 2021; 8.5K grade-school math word problems; cornerstone of reasoning evaluation."},
    {"id": "math-dataset", "name": "MATH dataset", "entity_type": "benchmark", "description": "Hendrycks et al. 2021; 12.5K competition-level math problems with step-by-step solutions."},
    {"id": "coco", "name": "MS COCO", "entity_type": "dataset", "description": "Lin et al. 2014; 330K images with 2.5M object instances, segmentation masks, and captions; defined dense vision supervision."},
    {"id": "visual-genome", "name": "Visual Genome", "entity_type": "dataset", "description": "Krishna et al. 2016; dense scene graphs with objects, attributes, and relations."},
    {"id": "sam-sa1b", "name": "Segment Anything / SA-1B", "entity_type": "dataset", "description": "Kirillov et al. Meta 2023; 11M images with 1.1B masks generated via model-in-the-loop annotation flywheel."},
    {"id": "ego4d", "name": "Ego4D", "entity_type": "dataset", "description": "Meta 2021; 3,670 hours of egocentric video; foundational for embodied-AI pretraining."},
    {"id": "open-x-embodiment", "name": "Open X-Embodiment / RT-X", "entity_type": "dataset", "description": "Oct 2023 consortium dataset across 22 robot embodiments and ~1M trajectories from 34 labs; enabled cross-embodiment transfer."},
    {"id": "droid", "name": "DROID", "entity_type": "dataset", "description": "Khazatsky et al. RSS 2024; 76K teleoperated trajectories, 350 hours, 564 scenes, 86 tasks, 13 institutions, Franka Panda-standardized, CC-BY-4.0."},
    {"id": "pdb", "name": "Protein Data Bank (PDB)", "entity_type": "dataset", "description": "RCSB repository of experimental protein structures (1971–); foundational substrate for AlphaFold."},
    {"id": "alphafold", "name": "AlphaFold 2/3", "entity_type": "product", "description": "DeepMind 2021/2024; solved protein structure prediction by combining PDB with MSA-derived co-evolution signals."},
    {"id": "roots-bloom", "name": "ROOTS / BLOOM", "entity_type": "dataset", "description": "BigScience 2022; 1.6TB multilingual corpus across 46 natural and 13 programming languages; trained BLOOM."},
    {"id": "nllb", "name": "NLLB-200", "entity_type": "product", "description": "Meta 2022 No Language Left Behind; MT across 200 languages with accompanying parallel data."},
    {"id": "madlad-400", "name": "MADLAD-400", "entity_type": "dataset", "description": "Google 2023; 3T tokens across 419 languages with document-level audits."},
    {"id": "aya", "name": "Aya Collection", "entity_type": "dataset", "description": "Cohere for AI 2024; 513M multilingual instruction instances across 114 languages, including 204K human-curated."},
    {"id": "bartz-v-anthropic", "name": "Bartz v. Anthropic", "entity_type": "benchmark", "description": "N.D. Cal., Judge Alsup, June 2025; training fair use but piracy-sourced library not; class-certified, settled Sept 2025."},
    {"id": "kadrey-v-meta", "name": "Kadrey v. Meta", "entity_type": "benchmark", "description": "N.D. Cal., Judge Chhabria, June 2025; fair-use ruling on Llama training with market-harm emphasis."},
    {"id": "nyt-v-openai", "name": "NYT v. OpenAI/Microsoft", "entity_type": "benchmark", "description": "Filed Dec 2023; motion to dismiss largely denied March 2025; proceeding to trial; includes contested preservation order."},
    {"id": "getty-v-stability", "name": "Getty v. Stability AI", "entity_type": "benchmark", "description": "UK and US cases against Stable Diffusion training on Getty-watermarked images; key test of image-copyright claims."},
    {"id": "re-laion-5b", "name": "Re-LAION-5B", "entity_type": "dataset", "description": "Aug 2024 re-release after Dec 2023 Stanford CSAM report; 2,236 links removed with IWF/C3P partnership."},
    {"id": "data-provenance-initiative", "name": "Data Provenance Initiative", "entity_type": "lab", "description": "Longpre et al. 2023–2024; audited licenses on 1,800+ datasets; 'Consent in Crisis' documented rapid robots.txt closure."},
    {"id": "common-pile", "name": "Common Pile", "entity_type": "dataset", "description": "EleutherAI 2024–2025 open-licensed-only corpus; reaches ~80% of mixed-corpus performance at 7B scale."},
    {"id": "openai", "name": "OpenAI", "entity_type": "company", "description": "Frontier lab whose GPT series, InstructGPT, Codex, and o1 defined several data paradigms; extensive 2024–2025 licensing deals."}
  ],
  "timeline": [
    {"id": "2009-06-20-imagenet-release", "date": "2009-06-20", "title": "ImageNet released at CVPR", "theme_ids": ["scale-unlocking-corpora", "annotation-dense-datasets"], "entity_ids": ["imagenet"], "body": "Deng, Li et al. publish ImageNet with 1.2M+ labeled images across 1,000 classes; three years later it triggers the deep learning era."},
    {"id": "2012-09-30-alexnet-ilsvrc", "date": "2012-09-30", "title": "AlexNet wins ILSVRC-2012", "theme_ids": ["scale-unlocking-corpora"], "entity_ids": ["alexnet", "imagenet"], "body": "Krizhevsky/Sutskever/Hinton cut top-5 error to 15.3% on ImageNet, proving deep CNNs at scale; the enabling artifact was the dataset."},
    {"id": "2014-05-01-coco-released", "date": "2014-05-01", "title": "MS COCO dataset released", "theme_ids": ["annotation-dense-datasets"], "entity_ids": ["coco"], "body": "Lin et al. release 330K images with 2.5M object instances, masks, and captions, defining dense vision supervision for a decade."},
    {"id": "2019-10-23-t5-c4", "date": "2019-10-23", "title": "T5 and C4 establish web-cleaning recipe", "theme_ids": ["quality-filtering-curation", "scale-unlocking-corpora"], "entity_ids": ["c4"], "body": "Raffel et al.'s C4 standardizes langID, boilerplate, and bad-word filters for Common Crawl; the template for nearly every subsequent web corpus."},
    {"id": "2020-05-28-gpt3-paper", "date": "2020-05-28", "title": "GPT-3 demonstrates in-context learning at 300B tokens", "theme_ids": ["scale-unlocking-corpora"], "entity_ids": ["gpt-3", "common-crawl"], "body": "Brown et al. show capability emergence at filtered-CC scale; begins the LLM pretraining data race."},
    {"id": "2020-12-31-the-pile", "date": "2020-12-31", "title": "The Pile released by EleutherAI", "theme_ids": ["scale-unlocking-corpora"], "entity_ids": ["the-pile"], "body": "825GB across 22 curated sources; substrate for GPT-J, Pythia, and most non-proprietary LLMs of 2021–2022."},
    {"id": "2021-07-15-alphafold2-nature", "date": "2021-07-15", "title": "AlphaFold 2 solves protein structure via PDB + MSAs", "theme_ids": ["domain-specific-unlocks"], "entity_ids": ["alphafold", "pdb"], "body": "Jumper et al. Nature paper demonstrates the clearest regime change from pairing a decades-old curated dataset with the right model."},
    {"id": "2021-07-07-gsm8k-release", "date": "2021-07-07", "title": "GSM8K defines LLM math evaluation", "theme_ids": ["domain-specific-unlocks"], "entity_ids": ["gsm8k"], "body": "Cobbe et al. release 8.5K grade-school math problems; becomes cornerstone of reasoning benchmarking."},
    {"id": "2021-08-24-laion-400m", "date": "2021-08-24", "title": "LAION-400M released", "theme_ids": ["scale-unlocking-corpora", "diversity-coverage-expansion"], "entity_ids": ["laion-5b"], "body": "Schuhmann et al. release 400M CLIP-filtered image-text pairs; predecessor to LAION-5B and Stable Diffusion's training substrate."},
    {"id": "2022-01-27-instructgpt", "date": "2022-01-27", "title": "InstructGPT paper establishes RLHF pipeline", "theme_ids": ["human-preference-alignment"], "entity_ids": ["instructgpt"], "body": "Ouyang et al. define SFT→RM→PPO; the template for every subsequent aligned LLM."},
    {"id": "2022-04-12-anthropic-hh", "date": "2022-04-12", "title": "Anthropic HH-RLHF dataset released", "theme_ids": ["human-preference-alignment"], "entity_ids": ["anthropic-hh"], "body": "~170K human preference pairs for helpfulness and harmlessness become the canonical open RLHF corpus."},
    {"id": "2022-11-03-the-stack", "date": "2022-11-03", "title": "The Stack released by BigCode", "theme_ids": ["domain-specific-unlocks", "provenance-and-licensing"], "entity_ids": ["the-stack"], "body": "6TB of permissively-licensed code; replaces opaque GitHub scrapes and becomes StarCoder's substrate."},
    {"id": "2022-12-15-constitutional-ai", "date": "2022-12-15", "title": "Constitutional AI / RLAIF", "theme_ids": ["human-preference-alignment", "synthetic-data-generation"], "entity_ids": ["constitutional-ai"], "body": "Anthropic shows model-written critiques can substitute for human harmlessness labels — first scaled AI-feedback result."},
    {"id": "2022-12-20-self-instruct", "date": "2022-12-20", "title": "Self-Instruct paper", "theme_ids": ["synthetic-data-generation"], "entity_ids": ["self-instruct"], "body": "Wang et al. bootstrap 52K instructions from a seed LM; sparks the distilled instruction-tuning era."},
    {"id": "2023-03-13-alpaca-released", "date": "2023-03-13", "title": "Stanford Alpaca released", "theme_ids": ["synthetic-data-generation"], "entity_ids": ["alpaca"], "body": "52K instructions from text-davinci-003 at ~$600; demonstrates cheap instruction tuning and triggers the open chat-model wave."},
    {"id": "2023-04-05-segment-anything", "date": "2023-04-05", "title": "Segment Anything / SA-1B released", "theme_ids": ["annotation-dense-datasets", "scale-unlocking-corpora"], "entity_ids": ["sam-sa1b"], "body": "Kirillov et al. release 11M images with 1.1B masks via model-in-the-loop annotation, a ~400× scale increase over prior segmentation data."},
    {"id": "2023-05-29-dpo-paper", "date": "2023-05-29", "title": "DPO collapses the RLHF pipeline", "theme_ids": ["human-preference-alignment"], "entity_ids": ["dpo"], "body": "Rafailov et al. reformulate preference optimization as a single contrastive loss, reshaping post-training economics."},
    {"id": "2023-06-01-refinedweb", "date": "2023-06-01", "title": "RefinedWeb shows web-only can match curated mixes", "theme_ids": ["quality-filtering-curation"], "entity_ids": ["refinedweb"], "body": "Penedo et al. TII paper; Falcon-40B on RefinedWeb matches LLaMA without books or code, upending priors on corpus composition."},
    {"id": "2023-06-20-phi-textbooks", "date": "2023-06-20", "title": "Phi-1 'Textbooks Are All You Need'", "theme_ids": ["synthetic-data-generation"], "entity_ids": ["phi"], "body": "Gunasekar et al. argue synthetic textbook-style data produces disproportionate small-model capability; begins the most contested line of data-centric work."},
    {"id": "2023-10-04-open-x-embodiment", "date": "2023-10-04", "title": "Open X-Embodiment / RT-X released", "theme_ids": ["domain-specific-unlocks"], "entity_ids": ["open-x-embodiment"], "body": "Cross-institution consortium releases 22-embodiment, ~1M-trajectory robot dataset from 34 labs; enables cross-embodiment transfer."},
    {"id": "2023-10-02-ultrafeedback", "date": "2023-10-02", "title": "UltraFeedback released", "theme_ids": ["human-preference-alignment"], "entity_ids": ["ultrafeedback"], "body": "Cui et al. release 64K × 4 GPT-4-labeled preferences; combined with DPO powers Zephyr-7B and becomes default open post-training corpus."},
    {"id": "2023-12-19-laion-csam-report", "date": "2023-12-19", "title": "Stanford identifies CSAM in LAION-5B", "theme_ids": ["provenance-and-licensing"], "entity_ids": ["re-laion-5b"], "body": "Stanford Internet Observatory finds 1,008 suspected CSAM URLs; LAION-5B pulled, Stable Diffusion 1.5 later withdrawn, triggers industry hygiene reckoning."},
    {"id": "2023-12-27-nyt-sues-openai", "date": "2023-12-27", "title": "New York Times sues OpenAI and Microsoft", "theme_ids": ["provenance-and-licensing"], "entity_ids": ["nyt-v-openai", "openai"], "body": "First major news-publisher copyright suit over LLM training data; proceeds to trial through 2025–2026 and reshapes licensing-deal dynamics."},
    {"id": "2024-03-19-droid-released", "date": "2024-03-19", "title": "DROID robot manipulation dataset released", "theme_ids": ["domain-specific-unlocks"], "entity_ids": ["droid"], "body": "Khazatsky et al. publish 76K teleoperated trajectories across 564 scenes and 13 institutions on standardized Franka Panda hardware."},
    {"id": "2024-05-08-alphafold3", "date": "2024-05-08", "title": "AlphaFold 3 extends to complexes", "theme_ids": ["domain-specific-unlocks"], "entity_ids": ["alphafold"], "body": "DeepMind extends protein structure prediction to protein-nucleic-acid and protein-ligand complexes, re-using and extending PDB-derived supervision."},
    {"id": "2024-05-31-fineweb-released", "date": "2024-05-31", "title": "FineWeb and FineWeb-Edu released", "theme_ids": ["quality-filtering-curation"], "entity_ids": ["fineweb", "fineweb-edu"], "body": "HuggingFace releases 15T-token FineWeb and its Llama-3-classified 1.3T-token educational subset with extensive ablations — largest open documented pretraining pipeline."},
    {"id": "2024-06-17-dclm-baseline", "date": "2024-06-17", "title": "DCLM-Baseline achieves 64% MMLU at 7B", "theme_ids": ["quality-filtering-curation"], "entity_ids": ["dclm"], "body": "Li et al. publish DCLM with a 240T-token pool and fixed training recipe; fastText-based filtering produces a 7B model at 64% MMLU on 2.6T tokens, a 6.6-point jump over MAP-Neo with 40% less compute."},
    {"id": "2024-07-24-shumailov-collapse-nature", "date": "2024-07-24", "title": "Model collapse paper in Nature", "theme_ids": ["synthetic-data-generation"], "entity_ids": ["shumailov-collapse"], "body": "Shumailov et al. demonstrate recursive training on self-generated data degrades models; Gerstgrasser et al. shortly after show accumulation (not replacement) avoids collapse."},
    {"id": "2024-08-30-re-laion-5b", "date": "2024-08-30", "title": "Re-LAION-5B released with CSAM removed", "theme_ids": ["provenance-and-licensing"], "entity_ids": ["re-laion-5b"], "body": "LAION partners with IWF, C3P, and Stanford to remove 2,236 links and re-release the dataset with new safety standards."},
    {"id": "2024-09-12-openai-o1-preview", "date": "2024-09-12", "title": "OpenAI o1 preview launches", "theme_ids": ["synthetic-data-generation", "domain-specific-unlocks"], "entity_ids": ["openai-o1"], "body": "First public reasoning model trained via RL on long chains-of-thought; starts the inference-time-scaling era."},
    {"id": "2025-01-20-deepseek-r1", "date": "2025-01-20", "title": "DeepSeek-R1 released with open reasoning-trace distillation", "theme_ids": ["synthetic-data-generation", "domain-specific-unlocks"], "entity_ids": ["deepseek-r1"], "body": "R1-Zero's pure-RL emergent CoT and R1-distilled Qwen-32B at 72.6% AIME 2024 make reasoning-trace distillation the dominant post-training paradigm; Nature publishes the peer-reviewed version in Sept 2025."},
    {"id": "2025-06-23-bartz-anthropic-ruling", "date": "2025-06-23", "title": "Bartz v. Anthropic fair-use ruling", "theme_ids": ["provenance-and-licensing"], "entity_ids": ["bartz-v-anthropic"], "body": "Judge Alsup rules AI training on lawfully-acquired books is 'quintessentially transformative' fair use but pirated library retention is not; class certification and $70B+ exposure force a Sept 2025 settlement."},
    {"id": "2025-06-25-kadrey-meta-ruling", "date": "2025-06-25", "title": "Kadrey v. Meta fair-use ruling", "theme_ids": ["provenance-and-licensing"], "entity_ids": ["kadrey-v-meta"], "body": "Judge Chhabria reaches similar fair-use conclusion two days after Bartz, emphasizing market-harm evidence as the decisive factor in future cases."}
  ],
  "open_questions": [
    {"id": "synthetic-pretraining-scaling", "question": "Does synthetic pretraining data (Phi/Cosmopedia-style) scale past ~14B parameters, or does it hit a benchmark-gaming ceiling that independent evaluations will continue to expose?", "theme_ids": ["synthetic-data-generation"], "priority": "high"},
    {"id": "reasoning-trace-transfer-limits", "question": "How far does R1-style reasoning-trace distillation transfer beyond math and code into domains without verifiable rewards (medicine, law, open-ended science), and is the quality ceiling set by the teacher model or by the verifier?", "theme_ids": ["synthetic-data-generation"], "priority": "high"},
    {"id": "data-wall-vs-filtering", "question": "Is the 'data wall' real, or is it an artifact of stopping before we learn to filter better? DCLM and FineWeb-Edu suggest most web tokens are still wasted; how many more MMLU points remain to be extracted from existing Common Crawl via better curation?", "theme_ids": ["quality-filtering-curation"], "priority": "medium"},
    {"id": "robotics-data-bottleneck", "question": "Can robotics reach a GPT-3-like scale moment via consortium data collection (Open X-Embodiment, DROID), or is embodiment-specific teleoperation inherently non-scaling, requiring a sim-to-real or video-learning breakthrough instead?", "theme_ids": ["domain-specific-unlocks"], "priority": "medium"},
    {"id": "preference-data-scaling-law", "question": "Is there a preference-data scaling law, or does quality dominate quantity past ~50K pairs? If the latter, the economics of alignment are structurally different from pretraining and DPO on small curated sets is near-optimal.", "theme_ids": ["human-preference-alignment"], "priority": "medium"},
    {"id": "model-collapse-in-practice", "question": "Does model collapse actually constrain frontier training in 2026 given that top labs accumulate rather than replace real data, or is it primarily a risk for downstream fine-tuners who train only on synthetic outputs?", "theme_ids": ["synthetic-data-generation"], "priority": "low"},
    {"id": "licensing-moat-durability", "question": "Will exclusive licensing deals (OpenAI-Reddit, Google-Reddit, OpenAI-News Corp) produce a durable data moat, or will court rulings on fair use (Bartz, Kadrey) commoditize access to copyrighted training data?", "theme_ids": ["provenance-and-licensing"], "priority": "high"},
    {"id": "multilingual-long-tail-approach", "question": "Is the right approach for low-resource languages real data collection (Masakhane, Aya) or LLM-translated synthetic data? Early evidence suggests translated synthetic works for benchmarks but leaves cultural and dialect gaps hard to quantify.", "theme_ids": ["diversity-coverage-expansion"], "priority": "low"},
    {"id": "process-vs-outcome-supervision", "question": "How much of reasoning-model capability comes from explicit process supervision (PRM800K-style step labels) versus outcome verification alone? DeepSeek-R1-Zero's emergent CoT from pure outcome RL argues the verifier carries most of the signal.", "theme_ids": ["human-preference-alignment", "synthetic-data-generation"], "priority": "medium"},
    {"id": "video-pretraining-bottleneck", "question": "Will open video pretraining ever reach LAION-scale parity given licensing complexity (WebVid takedown, Shutterstock deals), or will text-to-video remain dominated by labs with proprietary video library access?", "theme_ids": ["diversity-coverage-expansion", "scale-unlocking-corpora"], "priority": "medium"}
  ]
}
```
