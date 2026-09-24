# AI Problem Solving Workflow

## What the image should represent

Create a standalone workflow image showing how a person can use an AI assistant to approach a problem: defining the task, providing context, obtaining a proposed response, reviewing and independently checking it, refining the request when needed, and applying the checked result.

The title is **AI Problem Solving Workflow**. The subtitle should clarify **AI-assisted problem solving with human oversight**. Human and AI responsibilities must be visible throughout the diagram.

This is not a diagram of model training, hidden internal reasoning, software development or the implementation of a particular application. The workflow is a simplified process for using AI assistance; it does not imply that every system automatically performs every check.

## Main sequence

**Encounter a problem → Define the task and goal → Assemble context and constraints → Submit a prompt → AI processes the available input → Clarify if needed → AI generates a proposed response → Human reviews it → Human verifies important claims and steps → Decide whether the response is supported → Adapt the solution → Apply the checked result → Explain and reflect → Finish.**

There are two decision points:

1. **Clarification Needed?** If a missing detail or ambiguity is identified, obtain clarification before continuing.
2. **Response Supported?** If independent checks do not support the response, correct the context or approach and revise the request, solve independently, or seek suitable help.

## Detailed stages

| ID | Stage | Responsible actor | What happens | Output |
| --- | --- | --- | --- | --- |
| A01 | Encounter the Problem | Human | Recognize the question, difficulty or task. Decide that AI assistance could be useful. | An initial problem statement. |
| A02 | Define Task and Goal | Human | State the desired outcome, success criteria and kind of assistance needed: a hint, feedback, explanation or proposed solution. | A clear task specification. |
| A03 | Assemble Context and Constraints | Human | Supply relevant facts, conditions, examples, assumptions and any existing attempt. Include only information appropriate to share. | Context for the request. |
| A04 | Submit the Prompt | Human | Communicate the task and context to the AI assistant, including the requested scope or output format. | A submitted request. |
| A05 | Process Available Input | AI system | Process the prompt and the context available to the system. The available input may be limited and may not include an entire past conversation or external information. | Input for response generation. |
| A06 | Clarification Needed? | AI system / human | If an ambiguity or missing detail is identified, ask for or provide clarification. A system may overlook missing information, so later review is still necessary. | A clarified request or a decision to continue with stated assumptions. |
| A07 | Generate a Proposed Response | AI system | Generate a candidate answer, hint, explanation or feedback based on the request, available context and learned capabilities. The response can contain mistakes or unsupported assumptions. | A proposed response, not a verified result. |
| A08 | Review Relevance and Assumptions | Human | Check whether the response addresses the actual task. Look for missing constraints, misunderstood instructions, unsupported assumptions and contradictions. | A relevance review and identified concerns. |
| A09 | Verify Claims and Steps | Human | Use suitable calculations, tests, examples, reliable sources or expert input to check important parts of the response. Treat AI-suggested references as needing inspection. | Evidence supporting or challenging the response. |
| A10 | Response Supported? | Human | Decide whether the checks support using the response and whether it meets the original goal. Distinguish uncertainty from demonstrated error. | Acceptance, revision or an unresolved outcome. |
| A11 | Adapt and Decide | Human | Adapt the supported response to the actual situation. Choose what to use, explain any remaining assumptions and decide whether action is appropriate. | A usable, qualified solution. |
| A12 | Apply the Checked Result | Human | Use or communicate the result, with appropriate oversight for the task. | A practical outcome. |
| A13 | Explain and Reflect | Human | Explain the approach in their own words, compare it with any original attempt and identify what is still unclear. A later independent attempt can help examine understanding. | Reflection and possible follow-up practice. |
| A14 | Finish | Human | Close this attempt with the result and remaining limitations clearly recorded. | A completed assisted attempt. |

## Decision branches and revision loops

### Decision A06: Clarification Needed?

- **No:** Continue to A07 — Generate a Proposed Response.
- **Yes:** Go to a side box, **Ask / Provide Clarification**. The person supplies missing information or corrects the task description. Return to A03 — Assemble Context and Constraints, then submit the revised prompt through A04.
- This branch illustrates what should happen when ambiguity is recognized; it does not claim that AI reliably detects every gap.

### Decision A10: Response Supported?

- **Yes:** Continue to A11 — Adapt and Decide.
- **No / uncertain:** Go to a side box, **Correct Context or Approach**. Identify the failed check, clarify assumptions or provide reliable evidence. Return to A03 and request a revision if further AI assistance is useful.
- A person may instead work independently or consult another appropriate source. Repeatedly asking AI whether it is correct is not independent verification.
- If important uncertainty remains, record it and defer action or seek suitable help. Repeating the loop does not guarantee correctness.

## What belongs inside the AI portion

The main AI portion consists of **processing available input**, **requesting clarification when needed**, and **generating a proposed response**.

Do not automatically add “Search the Internet,” “Query a Database,” “Run Code,” or “Retrieve Verified Facts.” These require particular tools or integrations and are not universal capabilities of an AI assistant. If a future diagram includes tools, their outputs must still feed into review and verification.

Do not depict model training as something that happens whenever a user submits a prompt. Do not present the diagram as an account of a model's hidden internal thought process.

## Exact diagram connections

```text
START → A01 → A02 → A03 → A04 → A05 → A06

A06 — No → A07 → A08 → A09 → A10
A06 — Yes → Ask / Provide Clarification → A03

A10 — Yes → A11 → A12 → A13 → A14 → END
A10 — No / uncertain → Correct Context or Approach → A03
```

**Important:** The forward branch of A06 is **No** because the question is “Clarification Needed?” The forward branch of A10 is **Yes** because the question is “Response Supported?” Do not reverse these labels in the image.

Optional exit from A10: **Cannot verify → Record uncertainty / seek help → END**. Keep it separate from the successful path.

## Image-ready labels and actor tags

```text
START
01  Encounter the Problem                  [Human]
02  Define Task and Goal                   [Human]
03  Assemble Context and Constraints       [Human]
04  Submit the Prompt                      [Human]
05  Process Available Input                [AI]
06  Clarification Needed?                  [AI / Human]
07  Generate a Proposed Response           [AI]
08  Review Relevance and Assumptions        [Human]
09  Verify Claims and Steps                [Human]
10  Response Supported?                    [Human]
11  Adapt and Decide                       [Human]
12  Apply the Checked Result               [Human]
13  Explain and Reflect                    [Human]
14  Finish                                 [Human]
END

SIDE BOXES:
Ask / Provide Clarification                [AI / Human]
Correct Context or Approach                [Human]
```

## Visual design instructions

- **Title:** AI Problem Solving Workflow.
- **Subtitle:** AI-assisted problem solving with human oversight.
- Use a vertical flow with space on both sides for the clarification and correction loops.
- Use rounded rectangles for activities, diamonds for A06 and A10, and ovals for START and END.
- Give AI stages a restrained blue accent and human stages a teal accent. Keep actor tags visible so colour is not the only distinction.
- Use a neutral style for shared clarification, with the actor tag **AI / Human**.
- Use clear arrows and readable branch labels, especially the different Yes/No directions at A06 and A10.
- Use a high-resolution portrait canvas, a light background, dark text and consistent spacing.
- Avoid unsupported accuracy claims, speed comparisons and decorative elements that crowd the process.
- Add a small footer: **“AI proposes; people verify and decide.”**

## Ready-to-use ChatGPT image-generation prompt

Copy the following prompt into ChatGPT with this file attached:

> Generate one finished, high-resolution infographic titled **“AI Problem Solving Workflow”**, with the subtitle **“AI-assisted problem solving with human oversight.”** Use this attached file as the complete source. Create only this workflow; do not add a separate human-only comparison or a software development lifecycle.
>
> Use these exact numbered labels in the main flow:
> **START → 01 Encounter the Problem [Human] → 02 Define Task and Goal [Human] → 03 Assemble Context and Constraints [Human] → 04 Submit the Prompt [Human] → 05 Process Available Input [AI] → 06 Clarification Needed? [AI / Human] → 07 Generate a Proposed Response [AI] → 08 Review Relevance and Assumptions [Human] → 09 Verify Claims and Steps [Human] → 10 Response Supported? [Human] → 11 Adapt and Decide [Human] → 12 Apply the Checked Result [Human] → 13 Explain and Reflect [Human] → 14 Finish [Human] → END.**
>
> Make 06 and 10 decision diamonds. At **06 Clarification Needed?**, the **No** arrow continues to 07; the **Yes** arrow goes to a side box **Ask / Provide Clarification [AI / Human]**, then returns to 03. At **10 Response Supported?**, the **Yes** arrow continues to 11; the **No / uncertain** arrow goes to a side box **Correct Context or Approach [Human]**, then returns to 03. Keep the two loops visually distinct and route arrows outside boxes and text. Add a small side note: **“If verification is inconclusive, record uncertainty or seek help.”**
>
> Use rounded activity boxes, START/END ovals, a light background, dark readable text and generous spacing. Use restrained blue for AI stages, teal for human stages and a neutral colour for shared clarification. Include a small actor legend and keep the Human/AI tags on the boxes. Use a portrait layout tall enough for all 14 stages to remain readable. Use only the short labels inside boxes, not the detailed paragraphs.
>
> Add the footer **“AI proposes; people verify and decide.”** Do not depict AI output as automatically correct. Do not add web search, database access or code execution as universal steps. Do not invent research statistics, performance percentages or claims about hidden AI reasoning. Generate the actual workflow image, not instructions for drawing it.
