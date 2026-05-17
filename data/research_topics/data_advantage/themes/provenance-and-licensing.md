---
id: provenance-and-licensing
name: Provenance, Licensing, and the Legal Moat
description: >
  Changes to data availability, copyright interpretation, robots.txt
  enforcement, or licensing that affect which corpora can be used or
  re-released. Includes legal cases, policy shifts, and moat-building moves
  by labs or data holders.
origin: bootstrap
novelty_status: globally_novel
key_entity_ids:
- bartz-v-anthropic
- kadrey-v-meta
- nyt-v-openai
- re-laion-5b
- data-provenance-initiative
- common-pile
- openai
- getty-v-stability
created_at: '2026-04-25'
updated_at: '2026-04-25'
---
The competitive landscape of 2024–2026 is substantially shaped by legal and access shifts.

**Landmark rulings.** In **Bartz v. Anthropic** (N.D. Cal., Judge Alsup, June 23, 2025), training Claude on copyrighted books was ruled "quintessentially transformative" fair use — but downloading ~7M books from shadow libraries (LibGen, PiLiMi) was not. Class certification (482K works × up to $150K statutory damages) produced a reported settlement in Sept 2025. Two days later, **Kadrey v. Meta** (Judge Chhabria, June 25, 2025) reached a similar fair-use conclusion on training, but with more weight on market-harm evidence. These are district-court rulings, not appellate, and **they bless training while penalizing pirated sourcing** — meaning labs' legitimately-licensed data paths now matter for liability, not just PR.

**NYT v. OpenAI/Microsoft** (filed Dec 2023, motion to dismiss largely denied March/April 2025, proceeding to trial): the most consequential AI copyright case, complicated by a May 2025 preservation order forcing OpenAI to retain all user ChatGPT logs (over objections on privacy grounds, affirmed June 2025). A broader wave of suits (Authors Guild, Silverman, Getty Images v. Stability AI in UK and US, music publishers v. Anthropic) remains unresolved.

**LAION-5B CSAM incident.** Stanford Internet Observatory's Dec 2023 report found 1,008 suspected-CSAM URLs in LAION-5B. LAION pulled the dataset; Runway subsequently withdrew Stable Diffusion 1.5 from HuggingFace. **Re-LAION-5B** (Aug 2024) removed 2,236 links in partnership with IWF, C3P, and Stanford, and restored distribution. This is now the industry reference incident for web-scrape hygiene.

**Licensing deals as moat.** OpenAI has signed with AP, Axel Springer, FT, News Corp, Le Monde, Reddit, Stack Overflow, Shutterstock; Google with Reddit (~$60M/yr). These are increasingly exclusive and forward-licensed — meaning future open/smaller-lab models lose access to the same corpora. **The Data Provenance Initiative** (Longpre et al., 2023–2024; "Consent in Crisis" 2024) audited licenses on 1,800+ datasets and documented rapid closure: the share of web tokens behind robots.txt opt-outs for AI crawlers rose from ~1% to ~25% in a year for top domains.

**Open-licensed counter-efforts.** **Common Pile** (EleutherAI 2024–2025) and **KL3M** assemble public-domain and permissively-licensed corpora. Early ablations suggest open-licensed-only models can reach ~80% of mixed-corpus performance at the 7B scale — useful but not parity. **C2PA content credentials** and dataset cards/datasheets (Gebru et al., Mitchell et al.) remain the documentation substrate.

**Practical implication:** the durable data moat for frontier labs in 2026 is a combination of (a) licensed proprietary text/image/video deals, (b) user-conversation data from deployed products, and (c) in-house preference and reasoning-trace pipelines. For open-weight labs, it is (a) FineWeb/DCLM-scale filtered public corpora and (b) R1-style distillation from the largest open teacher. These bifurcate further each quarter.