This document contains information from the professor presentations.

Deliverable 1: Your protoype pitch
Your deliverable for today:
1) a one-sentence problem statement
2) a user description
3) an explanation why this problem is relevant to the user
4) a sketch how to solve this problem: input → NLP task → output.
5) SMART goals including sub-goals and non-goals

Deliverable 2: State of the Art
Your deliverable for today:
1) Scout the web for products/prototypes similar to your idea
2) Picture the landscape:
• Which products/prototypes already exist? (2–3 examples).
• What are their limitations/ why don’t they fit your problem/use case?
3) Reverse engineering
• Identify the common tech stack used by others: Name and briefly
describe the underlying methods/tools (e.g., LLMs, RAG, Vector DBs).
• Which parts can you potentially reuse?
4) Your delta / contribution
• How is your project different? What are you doing that fits better to your
specific use case?

Deliverable 3: User Experience
Your deliverable for today:
1) A Moodboard: Show screenshots of existing or simulated
apps/dashboards that have a fitting "vibe" to your project
2) The User Flow: A step-by-step diagram of the user interaction
with the app / system.
3) Some Feedback: Ask students on Zoom (or beforehand) about
potential issues in the user flow.
4) The experimental UI Design: Use Google Stitch (or other tools like
Figma) to sketch initial designs of your (web) app.

Deliverable 4: Agile Plan
Your deliverable for today:
1) Utilization of an agile Board (e.g. Jira.com)
2) A Backlog of 15-20 basic User Stories for the elements and stages
of your prototype (e.g. Jira Screenshot)
3) The MoSCoW Prioritization: Must, should, could, won‘t have
categorization for the user stories in the prototype.
4) The Acceptance Criteria for all the must and should user stories
5) The Story Point Estimation: How much effort for which story?
6) Your Sprint Plan for the next two weeks.

Deliverable 5: Data Strategy
Your deliverable for today:
1) Data Source: Where does the data come from?
2) Data Lineage: Who else has used this data? And how legal is it?
3) Pre-processing: What needs to be done?
4) Exploratory Showcase: This can be done with my data.
5) Applicability for your prototype: This is how I will use it.

Deliverable 6: NLP Modeling
Your deliverable for today:
1) Method & Model Choice: Which NLP approach and which model
and why?
2) Technical Setup: What stack, libraries, and access do you need?
3) Minimal Working Example: Code snippets that prove your NLP
core runs.
4) Sample Output & Observations: What does your model do with
the data?
5) What are critical points in order to scale this?

1. Method & Model Choice
Define what NLP method you are using and which concrete model executes it.
• Method: Identify the NLP task that fits your use case (e.g., Text Classification, Summarization, Named
Entity Recognition, Retrieval-Augmented Generation, Embedding Search).
• Model: Choose the specific model that performs this task (e.g., GPT-4o-mini, Llama-3-8B, a fine-
tuned BERT, SpaCy's de_core_news_lg).
• Justification: State why this combination fits your prototype better than the alternatives you
scouted in the State of the Art session.
The Deliverable:
• A clear statement of your Method (one sentence).
• A clear statement of your Model (name + version + provider).
• A short Rationale referencing your prototype's needs (language, domain, cost, privacy).

2. Technical Setup
Document the technical environment so anyone could rebuild it.
• Environment: Where does the code run? (Local machine, Google Colab, Hugging Face Space,
Jupyter Notebook).
• Libraries & Frameworks: Which key dependencies do you import? (e.g., transformers, langchain,
openai, spacy).
• Access & Credentials: How do you authenticate? (API keys, model downloads, Hugging Face
tokens).
• Briefly note the cost-per-call and approximate latency you observed — this matters later for
scaling.
The Deliverable:
• A Stack Slide listing: Environment, Top 3–5 Libraries, Access Method.
• A short note on Cost & Latency (one line is enough).

3. Minimal Working Example
Show the smallest possible piece of code that turns input into NLP output.
• Reduce to the core: Strip away everything that isn't the NLP step itself. No UI, no fancy preprocessing,
no error handling.
• Show the I/O flow: Input goes in → Model runs → Output comes out.
• Make it reproducible: A teammate should be able to copy-paste the snippet and get the same
result.
• You don't need to reveal everything — show enough to make the logic clear.
The Deliverable:
• A code snippet (5–20 lines) on a slide, ideally with syntax highlighting.
• A one-line description above it: "This is what turns our raw input into the NLP output."

4. Sample Outputs & Observations
Prove the model actually works on your real data — not on toy examples.
• Run the model on 3–5 real samples from the dataset you defined in the Data Strategy session.
• Capture Input → Output pairs in a table or side-by-side format.
• Observe qualitatively: Where does the output look right? Where does it surprise you? Where is it
merely "okay"?
• This is not a formal evaluation — that comes on June 5th. It is your first impression.
The Deliverable:
• A table or side-by-side view of 3–5 Input → Output pairs from real data.
• A short observation paragraph: What worked well? What was surprising?

5. What are Critical Points in order to Scale this?
Identify the bottlenecks that will become problems when you move from "5 samples in a notebook"
to "real prototype with real users."
• Cost at scale: What if you process 1,000 inputs instead of 5?
• Latency at scale: Is the per-call time acceptable when a user is waiting?
• Quality consistency: Did the model behave differently across your 5 samples? What if you run 100?
• Dependency risks: Are you locked into one provider's API? What happens if it's down or rate-limited?
• Data volume: Can your current setup handle the full dataset, or only a sample?
The Deliverable:
• A list of 2–4 concrete scaling concerns specific to your prototype.
• For each concern: a brief mitigation idea (no full solution needed yet).

Deliverable 7: End-2-End-Systems
Your deliverable for today:
1) Th System Architecture Blueprint: A structural diagram mapping the
complete pipeline across the LLMOps lifecycle: Data Ingestion (Build)
-> Model Inference (Run) -> User Interface (Deployment).
2) A Pipeline Component Breakdown: Documentation of the technical
hand-offs between components (e.g., how the JSON from the data
scraper feeds into the LangChain template).
3) The Walking Skeleton Demo: A live demonstration or screen
recording of the minimal working pipeline. Data enters, is pre-
processed, passes through the model, and an output is generated.
4) The Bottleneck & Debt Analysis: Identification of the weakest links in
the current pipeline and the immediate next steps to stabilize the
system.

1. The Architecture Blueprint
Goal: Map the entire system logic visually from backend to frontend.
The Work: Create a system architecture diagram (using draw.io, Excalidraw, or equivalent).
In this diagram, define the flow of data through the specific phases:
• Build: Data extraction, chunking, and vectorization logic.
• Run: Model inference, prompt injection, and retrieval (RAG) mechanics.
• Deployment: The frontend interface (e.g., Streamlit) and API endpoints.
The Deliverable: A clear, readable block diagram showing all components, databases, APIs, and the
user interface. Arrows must indicate the direction of data flow.

2. Pipeline Component Breakdown
Goal: Detail the specific transformations occurring between the blocks of your architecture.
The Work:
• Document the "Hand-offs." When data moves from the pre-processing script to the LLM, what
format is it in? (e.g., "The text is chunked into 500-token strings and passed as an array to the FAISS
index").
• Explicitly define the tools handling each transition (e.g., LlamaParse for PDF extraction, OpenAI API
for inference).
The Deliverable: A bulleted list or table explaining the exact data state and tool used at the three
critical junctions: Input -> Pre-processing, Pre-processing -> Model, and Model -> Output.

3. The "Walking Skeleton" (Live Demo)
Goal: Prove that the components can communicate with each other, even if the output is
rudimentary.
The Work:
• Connect your previously isolated data scripts with your baseline model.
• Feed a single piece of raw data through the pipeline.
• Ensure the output is successfully communicated to the user layer (even if it is just a print statement
in a terminal or a basic unstyled web text block).
• Please: No "mocked" data in the middle. The flow should be continuous.
The Deliverable: A 30-60 second live demo showing a raw input resulting in a model-generated
output.

4. Bottleneck Analysis & Next Steps
Goal: Prove that the components can communicate with each other, even if the output is
rudimentary.
The Work:
• Analyze the "Walking Skeleton." Which part is the most fragile, slowest, or most prone to failure?
• Common bottlenecks in NLP pipelines: Token limits exceeded, slow API response times, UI blocking
during inference, or catastrophic failure on edge-case data.
• Determine the engineering priority to fix these issues.
The Deliverable:
• Identification of the top 2 technical bottlenecks in the current architecture.
• A concrete list of the next 3 tasks to address these bottlenecks in the upcoming sprint.

Deliverable 8: Evaluation & Quality
Your deliverable for today:
1) Performance Metrics: Define and measure NLP-specific quality
metrics on a held-out test set.
2) Benchmark Comparison: Compare against a naive baseline
and an ablated version of your system.
3) Pipeline Efficiency Test: Measure latency, cost, and
throughput of the full end-to-end pipeline.
4) Error Analysis: Categorize and learn from your prototype’s
failure cases.
5) User Evaluation: Run a structured user study with real target
users.

1. Performance Metrics
Establish a quantitative baseline: what does “good” look like for your NLP task?
Goal: Select the metrics that match your NLP task and report results on a held-out test set.
The Work:
• Choose metrics appropriate to your task type: generative systems (ROUGE-L, BERTScore, BLEU),
retrieval systems (Precision@k, MRR, nDCG), classifiers (F1, AUC, accuracy).
• Create a held-out test set of at least 20–50 examples not used during development.
• Report at least 2 quantitative scores. Briefly justify why each metric is the right fit for your prototype.
The Deliverable: A metrics table with at least 2 scores on real test data, plus one sentence explaining
why each metric was chosen.

2. Benchmark Comparison
A number in isolation means nothing. Context makes it meaningful.
Goal: Prove that your technical choices actually improve results by comparing against two reference
points.
The Work:
• Baseline A (Naive): The simplest possible approach with no ML (e.g., first-N-sentences extraction,
majority class, keyword search).
• Baseline B (Ablation): Your system without its key NLP component (e.g., GPT-4o-mini with no RAG,
or a generic embedder instead of your domain-specific one).
• Score all three systems on the same test set using the same metric from Component 1.
The Deliverable: A side-by-side comparison table (Naive Baseline / Ablation / Full System) with
scores on the same metric. One sentence explaining the improvement.

3. Pipeline Efficiency Test
A model that takes 30 seconds or costs €5 per query is not a viable product.
Goal: Measure the real-world performance of the full pipeline under realistic conditions.
The Work:
• Latency: Time the full pipeline from raw input to output delivered to the user. Run 10+ samples and
report mean and worst-case.
• Cost: Calculate the cost per query (API tokens, compute). Project to 100 / 1,000 / 10,000 queries per
month.
• Bottleneck: Identify which pipeline stage contributes most to total latency.
The Deliverable: A table showing average latency (mean + worst case), cost per query, and
estimated monthly cost at three usage scales.

4. Error Analysis
Metrics tell you how much the system fails. Error analysis tells you why — and what to fix first.
Goal: Identify and categorize the failure modes of your prototype to prioritize the highest-leverage
improvements.
The Work:
• Review your test set outputs and flag every case where the system was wrong, incomplete, or
surprising.
• Group failures into named categories (e.g., “Hallucination”, “Retrieval miss”, “Formatting error”). Aim
for 3–5 categories.
• Show 1–2 concrete input/output examples per category. State the likely root cause.
The Deliverable:
A categorized error table (category / count / root cause / example), plus a prioritized list of the top 2–
3 fixes.

5. User Evaluation
Technical metrics measure what the system produces. Users measure whether it is actually helpful.
Goal: Test the prototype with real target users to find usability issues invisible to automated metrics.
The Work:
• Recruit 3-8 real target users
• Define 2–3 concrete tasks and ask users to complete them using the prototype.
• Collect: SUS questionnaire (10 standard items, 0–100 score), task success rate, and at least 1 direct
user quote per participant.
The Deliverable:
SUS score (graded A–F), task success rate, top 3 usability findings, and 1–2 direct quotes from users.

Deliverable 9: Optimizing your Prototype
Your deliverable for today:
1) Optimization Backlog: Turn your findings into a prioritized list of
engineering improvements.
2) Production Deployment Plan: Design the full stack architecture
for running your system with real users.
3) Monitoring & Observability: Instrument your system so quality
regressions are caught before users notice.
4) Model Optimization: Systematically improve NLP quality e.g.
through prompt engineering and caching.
5) First Production Sprint: Execute the top 3 backlog items and
measure the improvement.

1. Optimization Backlog
Planning without priorities is just a wish list. Structure your improvements before writing a single line
of code.
Goal: Convert every weakness identified in Deliverable 8 (error analysis, efficiency gaps, user
complaints) into a concrete, actionable backlog ticket.
The Work:
• For each finding, write one backlog item specifying: Impact (HIGH/MEDIUM/LOW), Effort (S/M/L), and
a clear Acceptance Criterion (how will you know it’s fixed?).
• Prioritize using Impact/Effort: P1 = HIGH impact + S/M effort. These go into the First Production Sprint
(Component 5).
• Aim for 5–8 items total. Fewer than 5 means you didn’t look hard enough. More than 10 means you
haven’t prioritized yet.
The Deliverable:
A prioritized table of 5–8 items (item / impact / effort / priority / acceptance criterion), sorted P1 first.

2. Production Deployment Plan
A Colab notebook is not a product. Map out your full production stack before writing deployment
code.
Goal: Design the target architecture that real users will interact with — from browser to model and
back.
The Work:
• Frontend: Where do users interact? (Streamlit, Gradio, custom React app). Where is it hosted?
• API Layer: How does the frontend talk to the model? (FastAPI, Flask, serverless function).
Containerized with Docker?
• Inference & Retrieval: Cloud API (OpenAI, Anthropic) or self-hosted model? Where does the vector
index live?
• Storage & Cache: What do you persist? (user sessions, cached results, logs). Which database or
cache?
The Deliverable:
A stack diagram (Frontend → API → Inference → Storage) plus one-sentence justification for each
layer’s technology choice.

3. Monitoring & Observability
NLP applications fail silently. A single prompt change can destroy quality with no error thrown.
Goal:
Instrument the system so you know immediately when quality, cost, or latency regresses — before
users file a complaint.
The Work:
• Request Logging: Define exactly what fields to log for every query: at minimum timestamp, input,
output, latency_ms, token_count, and cost_eur.
• Regression Test: Build one automated test that runs on every code push: a golden set of 10–20
fixed query/answer pairs scored by your D8 metric. CI fails if the score drops below threshold.
• Usage Dashboard: Track 3 key metrics in a simple dashboard: daily cost (€), p95 latency (ms),
error rate (%).
The Deliverable:
A monitoring plan table: what gets logged, what the regression test checks, and which 3 dashboard
metrics are tracked and at what alert thresholds.

4. Model Optimization
Before scaling infrastructure, squeeze more quality out of what you already have.
Goal:
Run at least 2 controlled experiments to improve NLP quality — measured against your D8 baseline —
before touching infrastructure.
The Work:
• Experiments: Change one thing of the input at a time (e.g. when using a prompt: A constraint, a
persona, a format instruction, a few-shot example). Re-run on the D8 test set and record the delta.
• Model swap: Consider whether a different model (larger, cheaper, or domain-fine-tuned) would
improve quality or reduce cost. Quantify the trade-off.
• Caching strategy: Identify the most frequent query patterns and define a cache key scheme.
Estimate the expected cache hit rate and latency saving.
The Deliverable:
A table of at least 2 tested changes (change description / metric before / metric after / verdict), plus
a one-paragraph caching strategy.

5. First Production Sprint
A backlog is not a deliverable. Show what you actually built and what changed as a result.
Goal:
Implement the top 3 P1 items from your Optimization Backlog and measure whether each acceptance
criterion was met.
The Work:
• Implement each of the 3 P1 backlog items. For each one, verify the acceptance criterion is met —
not just “I think it’s better”, but measured.
• Re-run your D8 core metric on the same test set. Report the new score alongside the original
baseline.
• Update the backlog: mark P1 items done, reprioritize the remaining P2 items for the next sprint.
The Deliverable:
Sprint review: 3 completed items with acceptance criterion result (✔/✖), before/after metric
comparison, and an updated backlog for the next sprint.

Deliverable 10: Storytelling & Reflection
Your deliverable for today:
1) The Hook & Narrative Arc
Craft the persona, before/after scenario, and elevator pitch that
make your demo memorable.
2) The Failure Post-Mortem
Transparently break down your biggest technical or process failure
and the exact pivot you took.
3) The Live-Demo Storyboard
Script every second of your demo — narration, latency gaps, and
backup plans.
4) The Lessons Learned Matrix
Categorize key insights across Technical vs. Procedural × Expected vs.
Surprising.

1. The Hook & Narrative Arc
Goal:
Turn your prototype from a feature list into a story. Make any audience understand why it matters in
under 60 seconds.
The Work:
Define one specific realistic target user (Persona). Write the concrete emotional scenario of their life
without your tool (Before), then with it (After). Distil the transformation into one sharp sentence.
The Deliverable:
A 3-part narrative outline:
(1) Persona card — one named user with a specific pain point.
(2)Before scenario — vivid description in 2–3 sentences.
(3)After scenario + one-sentence Elevator Pitch that starts with your product name.

2. The Failure Post-Mortem
Goal:
Demonstrate intellectual maturity: document the single biggest failure clearly and honestly — what
broke, why, and what you actually did about it.
The Work:
Choose the most impactful failure from any deliverable. Trace it from symptom to root cause.
Quantify the impact on your D8 metrics. Describe the pivot and measure whether it worked.
The Deliverable:
A structured table with five fields:
(1) What failed,
(2)When discovered,
(3)Root cause,
(4)Measurable impact on metrics from Deliverable 8
(5)Pivot taken and its outcome. One row per field.

3. The Live-Demo Storyboard
Goal:
Eliminate dead air and demo anxiety on July 3rd by scripting every step of your 5–7 minute live demo
before you face the audience.
The Work:
Map the complete demo flow from opening the app to delivering the final result. For each step, plan
the screen state, exactly what you say, any latency gap, and your fallback if the API is slow or fails.
The Deliverable:
A storyboard table with minimum 5 rows: Step / Screen State / Narration Script / Latency Risk /
Backup Action. Narration must explicitly cover latency gaps — never go silent while the model thinks.

4. The Lessons Learned Matrix
Goal:
Distil the most transferable knowledge from the entire project into a structure that separates what
you confirmed from what genuinely surprised you.
The Work:
Categorize key insights: rows = Technical vs. Procedural; columns = Expected vs. Surprising. Minimum
2 insights per quadrant. Then write one “Most Valuable Lesson” sentence synthesizing the takeaway
you’d give next year’s students.
The Deliverable:
A completed 2×2 matrix as a table, minimum 2 insights per cell, plus one “Most Valuable Lesson”
sentence below the table.
