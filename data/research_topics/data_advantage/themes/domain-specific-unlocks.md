---
id: domain-specific-unlocks
name: Domain-Specific Unlocks
description: >
  Datasets that enable strong performance in a narrow technical domain:
  The Stack for code, MATH/GSM8K for reasoning, Open X-Embodiment for
  robotics, PDB for protein structure, domain-specific scientific corpora.
origin: bootstrap
novelty_status: globally_novel
key_entity_ids:
- the-stack
- humaneval
- gsm8k
- math-dataset
- prm800k
- open-x-embodiment
- droid
- ego4d
- pdb
- alphafold
- sam-sa1b
created_at: '2026-04-25'
updated_at: '2026-04-25'
---
**Code.** GitHub scrapes enabled **Codex** (OpenAI 2021) and its product Copilot — the first data-driven product moat from training corpus access. **The Stack** (BigCode/HuggingFace 2022, 6TB permissively licensed) and **The Stack v2** (Feb 2024, 900B tokens, paired with Software Heritage archive) replaced opaque scrapes with documented, license-filtered code. StarCoder and StarCoder2 trained on them; DeepSeek-Coder, Qwen-Coder, and Code Llama use closely related mixes. **HumanEval** (Chen et al. 2021) and **MBPP** became the universal code benchmarks; **SWE-bench** (Jimenez et al. 2023) shifted the goalposts toward real repo-level tasks.

**Math and reasoning.** **GSM8K** (Cobbe et al., OpenAI 2021; 8.5K grade-school problems) and **MATH** (Hendrycks et al. 2021; 12.5K competition problems) defined the evaluation ladder. **PRM800K** (Lightman et al. 2023) introduced step-level process reward labels and validated process-reward models. **OpenWebMath** (Paster et al. 2023, 14.7B tokens), **MetaMathQA**, **OpenMathInstruct** (NVIDIA 2024, 1.8M problem-solution pairs), and **NuminaMath** (2024, AIMO winner) scaled training corpora. The current frontier is formal math: **MiniF2F**, **ProofNet**, and **Lean-Mathlib** as training+eval targets for AlphaProof-style systems.

**Robotics.** Robot manipulation data is the single biggest bottleneck in modern AI. **Ego4D** (Meta 2021, 3,670 hours egocentric video) provided observational grounding. **RT-1** (Google 2022, 130K episodes on Everyday Robots) established scale collection. **Open X-Embodiment / RT-X** (Oct 2023, 22 embodiments, ~1M trajectories from 34 labs) was the first cross-institution consortium dataset and the precondition for RT-2-X's positive transfer across embodiments. **DROID** (Khazatsky et al., RSS 2024) is the current reference: **76K teleoperated trajectories, 350 hours, 564 scenes, 86 tasks, 13 institutions, all on a standardized Franka Panda platform**, released CC-BY-4.0. Octo and Pi-0 (Physical Intelligence 2024) are DROID/OXE-trained generalist policies. Robotics remains a domain where **hardware-standardized, teleoperation-collected data is non-substitutable by synthetic or video** — a rare counterexample to the scraping-plus-synthesis default.

**Biology.** The **Protein Data Bank** (PDB, RCSB, founded 1971; ~220K structures) is the foundational corpus; **AlphaFold 2** (Jumper et al., Nature 2021) used PDB plus UniRef/BFD multiple-sequence alignments to solve protein structure prediction at near-experimental accuracy, the clearest single case of a decades-old curated dataset enabling a regime change once paired with the right model. **AlphaFold 3** (May 2024) extended to complexes with nucleic acids and ligands. **ESM-2 / ESM-3** (Meta/EvolutionaryScale) pretrain on UniRef-50/90 at scale; **GNoME** (DeepMind 2023) discovered 2.2M new crystals from Materials Project-scale data.

**Vision-dense annotation.** **MS COCO** (Lin et al. 2014, 330K images, 2.5M object instances, 5 captions each) defined detection/segmentation/captioning for a decade. **Visual Genome** (Krishna et al. 2016), **ADE20K**, **Cityscapes**, **LVIS** filled niches. **Segment Anything / SA-1B** (Kirillov et al., Meta 2023) — **11M images, 1.1B masks, the largest segmentation dataset by ~400×** — was generated through a model-in-the-loop annotation flywheel and enabled zero-shot segmentation as a primitive.