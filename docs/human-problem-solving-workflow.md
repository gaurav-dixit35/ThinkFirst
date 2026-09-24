# Human Problem Solving Workflow

## What the image should represent

Create a standalone workflow image showing how a person can work through a problem independently: understanding it, recalling relevant knowledge, developing an approach, attempting a solution, checking it, revising it and reflecting on the result.

This is a **human problem-solving process**, not a software development lifecycle, app navigation diagram or comparison with AI. This file contains everything needed to generate the image independently.

“Independent” means the person develops the solution themselves. They may consult books, notes, observations or other non-AI sources. The diagram is a simplified, deliberate approach; actual thinking can be nonlinear and people may revisit earlier steps.

## Main sequence

**Identify the problem → Define the goal → Identify facts and constraints → Recall relevant knowledge → Check information sufficiency → Explore approaches → Choose a plan → Attempt the solution → Verify the result → Decide whether it meets the goal → Explain the reasoning → Apply the solution → Reflect and learn → Finish.**

There are two decision points:

1. **Enough information?** If not, gather information and update the problem understanding.
2. **Solution supported?** If not, identify the issue, revise the plan and attempt it again.

## Detailed stages

| ID | Stage | What the person does | Output |
| --- | --- | --- | --- |
| H01 | Identify the Problem | Notice a question, obstacle or task. State what needs to be solved rather than immediately guessing an answer. | An initial problem statement. |
| H02 | Define the Goal | Clarify the desired result, audience or use, and what would count as a satisfactory solution. | A goal and success criteria. |
| H03 | Identify Facts and Constraints | Separate known facts, unknowns and assumptions. Note relevant limits such as available resources, time, conditions or permitted methods. | A clear description of available information and restrictions. |
| H04 | Recall Relevant Knowledge | Retrieve useful concepts, formulas, experiences and similar examples. Recognize where existing knowledge may not be sufficient. | Relevant knowledge and possible gaps. |
| H05 | Enough Information? | Decide whether the available information is sufficient to make a meaningful attempt. Complete certainty is not required, but important assumptions should be visible. | A decision to proceed or gather more information. |
| H06 | Explore Possible Approaches | Consider alternative methods. Break a complex task into smaller parts where useful. Estimate which approaches fit the goal and constraints. | One or more candidate approaches. |
| H07 | Choose and Plan | Select an approach and outline the next steps. Decide how the eventual result will be checked. | A practical plan. |
| H08 | Attempt the Solution | Carry out calculations, write an explanation, build an argument, design something or test an idea. Keep track of intermediate work and uncertainties. | A candidate solution and supporting work. |
| H09 | Verify the Result | Check calculations, logic, examples, evidence and assumptions against the goal. Where appropriate, use a different method or a counterexample rather than merely rereading. | Evidence supporting the result, or identified errors and gaps. |
| H10 | Solution Supported? | Decide whether the checks support using the solution and whether the success criteria have been met. Open-ended tasks may have several acceptable solutions. | Acceptance, revision or an unresolved outcome. |
| H11 | Explain the Reasoning | State why the solution follows, describe important assumptions and identify limitations. If the explanation exposes a gap, return to verification. | An understandable, qualified explanation. |
| H12 | Apply the Solution | Use the checked result, communicate the answer or carry out the intended action when appropriate. | A practical outcome. |
| H13 | Reflect and Learn | Review which approaches worked, where mistakes occurred and what could be done differently on a similar task. Record useful insights if desired. | A reflection that may support future problem solving. |
| H14 | Finish | Close this attempt with the outcome and remaining uncertainty clearly recorded. | A completed attempt, not a claim of perfect knowledge. |

## Decision branches and revision loops

### Decision H05: Enough Information?

- **Yes:** Continue to H06 — Explore Possible Approaches.
- **No:** Go to a side box, **Gather Missing Information**. Consult an appropriate reference, inspect the situation, ask for clarification or identify a missing fact. Return to H03 — Identify Facts and Constraints.
- If important information cannot be obtained, record the limitation. Do not invent the missing facts.

### Decision H10: Solution Supported?

- **Yes:** Continue to H11 — Explain the Reasoning.
- **No / uncertain:** Go to a side box, **Identify Error and Revise**. Reconsider the method, intermediate steps or assumptions. Return to H07 — Choose and Plan, then attempt and verify again.
- If the goal itself was misunderstood, return to H02 instead. This is an explanatory exception; the image needs only the main revision loop to H07.
- If the problem remains unresolved, seek suitable help or record an unresolved outcome. The diagram should not imply that repeating the loop guarantees success.

### Later review

Applying a solution can reveal new evidence. In practice, the person may reopen the problem. Show this only as a small optional dashed feedback arrow if there is enough space.

## Exact diagram connections

Use these connections so arrow direction is unambiguous:

```text
START → H01 → H02 → H03 → H04 → H05

H05 — Yes → H06 → H07 → H08 → H09 → H10
H05 — No → Gather Missing Information → H03

H10 — Yes → H11 → H12 → H13 → H14 → END
H10 — No / uncertain → Identify Error and Revise → H07
```

Optional exit from either decision: **Cannot proceed → Record uncertainty / seek help → END**. Place it as a small side branch, not on the successful path.

## Image-ready labels

These short labels are the exact text to put inside the boxes. Use the detailed descriptions as context, not additional text in the image.

```text
START
01  Identify the Problem
02  Define the Goal
03  Identify Facts and Constraints
04  Recall Relevant Knowledge
05  Enough Information?
06  Explore Possible Approaches
07  Choose and Plan
08  Attempt the Solution
09  Verify the Result
10  Solution Supported?
11  Explain the Reasoning
12  Apply the Solution
13  Reflect and Learn
14  Finish
END

SIDE BOXES:
Gather Missing Information
Identify Error and Revise
```

## Visual design instructions

- **Title:** Human Problem Solving Workflow.
- **Subtitle:** From understanding a problem to checking and reflecting on a solution.
- Use a spacious vertical flow with a left or right margin reserved for revision loops.
- Use rounded rectangles for activities, diamonds for H05 and H10, and ovals for START and END.
- Use solid arrows for the main path and clearly labelled side arrows for decisions.
- Use a light background, dark text and restrained green or teal accents.
- Keep all labels readable at normal presentation size. Prefer a high-resolution portrait canvas rather than shrinking the text.
- Avoid decorative brain imagery that crowds the process, performance percentages and intelligence scores.
- Add a small footer: **“A deliberate process; verification may lead to revision.”**

## Ready-to-use ChatGPT image-generation prompt

Copy the following prompt into ChatGPT with this file attached:

> Generate one finished, high-resolution infographic titled **“Human Problem Solving Workflow”**. Use this attached file as the complete source. Create only the human workflow; do not add an AI comparison or a project development lifecycle.
>
> Use this exact main sequence:
> **START → 01 Identify the Problem → 02 Define the Goal → 03 Identify Facts and Constraints → 04 Recall Relevant Knowledge → 05 Enough Information? → 06 Explore Possible Approaches → 07 Choose and Plan → 08 Attempt the Solution → 09 Verify the Result → 10 Solution Supported? → 11 Explain the Reasoning → 12 Apply the Solution → 13 Reflect and Learn → 14 Finish → END.**
>
> Make **05 Enough Information?** and **10 Solution Supported?** decision diamonds. Label each forward arrow **Yes**. From 05, draw a **No** arrow to a side box **Gather Missing Information**, then return to 03. From 10, draw a **No / uncertain** arrow to a side box **Identify Error and Revise**, then return to 07. Keep the return arrows outside the main column and do not cross text or boxes. Include a small side note: **“If unresolved, record uncertainty or seek help.”**
>
> Use rounded activity boxes and START/END ovals, a light background, dark readable text, restrained green or teal accents and generous spacing. Make a clean academic diagram suitable for a project report or presentation. Use a portrait layout with enough height to keep all 14 stages readable. Do not squeeze detailed paragraphs into the boxes; use only the exact short labels above.
>
> Add the subtitle **“From understanding a problem to checking and reflecting on a solution.”** Add the footer **“A deliberate process; verification may lead to revision.”** Do not invent experimental results, completion rates, brain scores or claims that humans always solve problems correctly. Generate the actual workflow image, not instructions for drawing it.
