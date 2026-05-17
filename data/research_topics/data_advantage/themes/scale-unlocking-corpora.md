---
id: scale-unlocking-corpora
name: Scale-Unlocking Corpora
description: >
  Datasets that opened new capability regimes by providing sufficient scale
  for a training paradigm — Common Crawl for language models, LAION for
  open diffusion, The Pile and RedPajama for open LLM pretraining.
origin: bootstrap
novelty_status: globally_novel
key_entity_ids:
- imagenet
- common-crawl
- the-pile
- c4
- laion-5b
- refinedweb
- gpt-3
- alexnet
created_at: '2026-04-25'
updated_at: '2026-04-25'
---
The deep-learning era begins not with AlexNet but with **ImageNet** (Deng et al. 2009; ILSVRC benchmark 2010–2017). Fei-Fei Li's insistence that the bottleneck was data, not models, turned out to be correct: Krizhevsky, Sutskever, and Hinton's 2012 AlexNet win on ILSVRC-2012 (top-5 error 15.3% vs. 26.2%) was a model paper, but the enabling artifact was the 1.2M labeled training images. Every supervised-vision result for the next five years (VGG, ResNet, Inception, DenseNet) was an ImageNet-pretrained model. **Transfer learning as a paradigm is downstream of a single dataset.**

For text, **Common Crawl** (non-profit web crawl founded 2007, ~250B pages to date) is the substrate. GPT-2's **WebText** (Radford et al. 2019) filtered CC by outbound-Reddit karma; GPT-3 (Brown et al. 2020) trained on ~570GB of filtered CC plus Books, Wikipedia, and WebText2 — roughly 300B tokens total, the first demonstration that in-context learning emerges at scale. **The Pile** (Gao et al., EleutherAI 2020) — 825GB across 22 curated sources (PubMed, ArXiv, GitHub, Books3, Stack Exchange, etc.) — was the open answer and powered every non-proprietary LLM from GPT-J to Pythia. **C4** (Colossal Clean Crawled Corpus; Raffel et al. 2019 as part of T5) and its mC4 multilingual variant established the basic web-cleaning recipe (langID, boilerplate removal, bad-word filters) still used today. **RefinedWeb** (Penedo et al., TII 2023) showed for the first time that heavy deduplication plus aggressive filtering on web-only data matches curated mixes — Falcon-40B trained on RefinedWeb reached near-LLaMA performance without books or code. **RedPajama-v1** (Together AI 2023) open-reproduced LLaMA's 1.2T-token mix; **RedPajama-v2** (2023) scaled to 30T tokens of CC with quality signals.

For image-text, **LAION-400M** (Schuhmann et al. 2021) and **LAION-5B** (2022) — open CLIP-filtered image-URL-caption pairs — were the direct precondition for Stable Diffusion 1.x. They remain the clearest case of an open dataset producing an entire generative-model ecosystem. For video, **HowTo100M** (2019), **WebVid-10M** (2021, since withdrawn over licensing), **Panda-70M** (2024), and **OpenVid-1M** (2024) have played analogous but weaker roles — video pretraining data is still the bottleneck, not modeling, in text-to-video.

**What the evidence says in 2026:** the "scale unlocks capabilities" story holds for pretraining regime shifts (supervised vision → self-supervised language → multimodal → reasoning), but the incremental gain from adding raw web tokens beyond ~15T has flattened. This is why the action moved to filtering.