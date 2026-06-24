# Brand — Twitter

## tweet.md

Central log of all published tweets, in reverse chronological order.

Each entry uses this format:

```
---
date: YYYY-MM-DD
type: decision | epistemic | tension
---
Tweet text here.
```

The `type` field gives a machine reading this file enough context to understand the intent and voice of past tweets, and to help draft new ones consistently.

Each tweet is a self-contained mini story: what Distill is doing at that layer, the problem that arose, the tradeoff, and the decision. The problem lives in the tweet body — a technical reader should be able to understand the context, challenge the tradeoff, or contribute without knowing the codebase.

---

## Tweet Types

### Decision

The most common type. One non-obvious choice made while building. The formula: what I needed to do, what the obvious answer was, why I didn't take it.

The commit is evidence, not the subject. The subject is the intellectual problem. Link the commit for people who want to go deeper — keep the code out of the tweet body.

### Epistemic update

Distill is a belief-tracking system, so use it. A signal moved confidence in a thesis claim — up or down. Post the update with the reason it matters.

Format roughly: "Signal from [source] moved my confidence in [claim] from X toward Y, because..."

This directly demonstrates the product while building the research brand.

### Tension

A design question being sat with, a tradeoff with no clean answer, something not yet resolved. These generate replies and position the author as someone thinking, not just shipping. Post when something genuinely unresolved is worth naming.

---

## Voice

Matches the blog: introspective, intellectually honest about uncertainty. Prefer "here's what I was wrong about" over "I solved X." The commit is proof of the work, not the point of the tweet.

Post when there is something genuinely interesting to share, not on a fixed cadence.

---

## My voice

Raw writing samples — use these to calibrate tone, not the LLM-drafted tweets in tweet.md.

**Business retrospective (2021)**

> During the first half of 2021 I developed an app in partnership with a preschool in Dakar. The app train children to better write graphism and letters.
>
> During the second half of the year I sold a subscription (7.5 euro / month) during 4 months to Mr.Aly to use the app with his 4 years old daughter.
>
> The good point was to validate the existence of a market and the possibility of a subscription revenue model.
>
> Yet, I think that M.Aly is at the periphery of the market. Indeed, his daughter was already good, and he wanted her to skip a class.
>
> The bad point was that my channel hypothesis was wrong. I started a website where I focused on producing content for parents. Unfortunately the page views and number of subscribers to my mailing list did not grew as I expected.
>
> This last trimester I have pivoted my customer hypothesis and how to reach them. I will focus on producing content for parents with dyslexic children. I will do it on YouTube.

**Book summary**

> First let's consider luck not as a mystical superpower but as a psychological state of mind. The state of mind of people qualifying themselves as lucky people. Do these people have certain personality traits? It turns out yes.
>
> They maximize their chances by having a strong network providing them with information and opportunities beyond their reach. They are calm, relaxed and open to new experiences.
>
> They trust their gut or intuition about people and events.
>
> They expect success in their future and try to reach their goal even if the chances are slim. When they meet new people, they expect good attitude toward them.
