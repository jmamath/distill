---
id: annotation-dense-datasets
name: Annotation-Dense Datasets
description: Datasets with rich structured supervision (boxes, masks, captions, scene
  graphs, reasoning traces) that encode priors self-supervision cannot reach efficiently.
origin: bootstrap
novelty_status: globally_novel
key_entity_ids:
- coco
- visual-genome
- sam-sa1b
- open-x-embodiment
- droid
- prm800k
- openthoughts
created_at: '2026-04-25'
updated_at: '2026-04-25'
---
The unifying thread here is that **structured supervision encodes a prior that self-supervision cannot reach efficiently.** ImageNet (class labels), COCO (boxes, masks, captions), Visual Genome (scene graphs), RefCOCO (grounding phrases), Kinetics (action), AudioSet (audio-event labels): each added one annotation type and enabled a sub-field.

SA-1B's 1.1B masks exemplify the modern version — **dense annotation via a model-in-the-loop flywheel**, where an initial model assists human annotators, its outputs are corrected, and the improved model assists the next round. This cut per-mask cost by ~100× and produced a foundation-model-quality training set in ~12 months. The same pattern now appears in **OpenThoughts** (R1 generates traces, humans/filters curate) and in robotics (DROID scripts randomized scene perturbations during teleoperation).

Chain-of-thought annotations in datasets like **ScienceQA**, **MathInstruct**, and **BIG-Bench Hard** can be seen as annotation-dense math/reasoning corpora. The frontier question: how much of the value is the reasoning steps themselves versus the final answer plus a good verifier?