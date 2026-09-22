Controlled AI assistant
=======================

Project chat and chart vision (v1.3.3)
---------------------------------------------

For an institute-managed DeepSeek Harness account, use **Read local DeepSeek
Harness configuration** in AI settings. The Harness SDK route calls the installed
official dsh runtime; the app does not extract its model credentials or bypass it
with direct API requests. Install and configure Harness separately using
https://deepseek.com/harness/en/ .

Allow on-demand project data, results and conversation queries in the send preview.
The model can then query specific units, events, trials, spike times and result
tables through a local MCP interface, with evidence values and snapshot identifiers.
Try: “Query unit 25's SNR and ISI violation rate and explain the limitations.”
By default, chart metadata is not image-pixel access; raw voltage is not sent by
the project-query interface.

Chats are project-specific and can be assigned to Project, Figures, Methods, General,
or Earlier groups in the expanded chat window. A new chart-interpretation thread is
grouped under Figures automatically; users can change its group. The first question
automatically titles a thread, and titles can be renamed. Search matches groups,
titles and message text. This grouping is inside NeuroEphys AI; it does not alter
the separate Harness website conversation sidebar. Older flat history is
preserved as **Earlier conversation**. The current thread's recent turns, not all
threads mixed together, accompany each request. Threads are saved to the project's
``ai/conversation.json`` and can be searched after reopening it. Each request uses a fresh project snapshot. Switching
projects or provider settings requires renewed context approval. Analysis proposals
still require user confirmation and pass the existing application validators.
New analysis features require explicit tool registration; arbitrary shell, code
execution and file-system access are not granted.

To let the model actually inspect the current chart, choose **Chart** in the right
panel or **Interpret current chart** in the expanded conversation. The app renders
only that chart to PNG in memory and displays the exact image for approval before
sending it as an official Harness SDK image block. Image bytes are not stored in
the chat archive; only the chart label and send record are kept. A chart may show
raw traces or labels, so check the preview. Visual impressions are not substitutes
for numerical results. This feature currently requires the Harness SDK provider;
other API profiles do not silently pretend to see an image.

If ``NVM4306`` appears, the local Node/NVM trusted launcher blocked ``dsh``
before the request reached the model. Check ``dsh --version`` and have the
machine administrator run ``nvm reshim`` or repair the trusted launcher. Do not
work around it by copying institute credentials into the app.

**Enter** sends, and **Shift+Enter** inserts a new line. General research and other
questions are welcome even without an open project. For app-specific procedures,
the assistant can query the versioned built-in tutorial. It distinguishes general
model knowledge from measured project evidence and must not present unverified
current information or invented citations as checked facts.

Chats started without a project are kept separately at
``<user workspace>/ai/general_conversation.json`` and are not inserted into any
experiment project's chat archive.

After a multi-session Study is saved, the active project summary registers its
random Study ID, animal/session counts, selected conditions, validation level,
and available metrics. AI can explain the evidence and, in Collaborative mode,
propose the controlled ``run_multi_session_analysis`` action. The application still
checks the local Study, validates parameters, and asks the user to confirm. Study
names, local paths, animal/session row identities, large trajectories, and raw
voltage are excluded from the cloud summary. The assistant must distinguish
session-held-out from animal-held-out validation and must not match cells by Unit ID.

Read the answer first; open detail when needed
-----------------------------------------------

AI conversations default to **Concise** view. A response card leads with the
conclusion, keeps at most three decision-relevant points, and separates project
evidence reads, pending actions, the next step, and important warnings. The full
answer, scientific interpretation, limitations, evidence identifiers, and proposed
actions are preserved behind **View full answer and evidence**. Both the right-side
assistant and expanded dialog can switch between **Concise** and **Full**, and the
choice is remembered.

The model follows the same clarity contract before presentation is applied: answer
the question first, then add **Why**, **What to do now**, and **Important limitation**
only when useful. Internal field names must be translated into scientific meaning,
and every number needs an object, unit, and interpretation. Simple questions stay
short; result explanations and procedures may expand when clarity requires it.

This changes presentation, not scientific safeguards. Unsupported conclusions,
limitations, and safety-critical warnings remain visible. The original answer is
still stored in ``ai/conversation.json`` for review and audit. By default the model
does not narrate internal query plumbing, raw logs, or long parameter dumps unless
the user explicitly asks for detail.

The AI assistant occupies a collapsible right-side panel beside the active
analysis. It receives a small structured project summary produced by local
deterministic code. Raw voltage arrays are excluded.

Operating modes
---------------

Manual
   No model request is made. All scientific controls remain available.

Assistant
   The model explains the current page, parameters, warnings, and possible next
   steps. It cannot execute a tool.

Collaborative
   The model may propose a whitelisted tool call. NeuroEphys AI validates the
   schema, prerequisites, dependencies, workflow order, and risk. The user sees
   a confirmation dialog before execution.

Providers
---------

The current provider layer supports DeepSeek, OpenAI Responses,
OpenAI-compatible endpoints, an institute-managed harness,
laboratory/private compatible services, and local Ollama. Provider URL, model,
timeout, retries, streaming, and reasoning options are configurable. API keys
are stored in the operating-system credential service or current session and
are excluded from projects, logs, exports, and Git.

When DeepSeek Harness is installed locally, select **Import installed DeepSeek
Harness**. The app reads only non-secret provider metadata: the endpoint, model
list, default model, and credential environment-variable name. It never opens
the Harness credential file. Plain HTTP remains blocked unless the user enables
it for that specific trusted private-network provider, after which **Check
service** validates the model list and latency.

The Harness SDK route calls the installed official ``dsh`` runtime. It is not UI
automation of the Harness website and does not copy institutional credentials into
the app. Harness supplies model access; NeuroEphys AI owns the project snapshot,
MCP queries, tool validation, scientific constraints, audit trail, and user
confirmation. Generic APIs and Ollama remain available for other users.

Cloud-data preview
------------------

Before an online request, **Preview cloud data** lists the selected field
categories. Users may remove optional fields or cancel. Local paths, raw
voltage, large arrays, and API credentials are redacted.

Scientific response structure
------------------------------

Result explanations are divided into observed results, statistical evidence,
possible biological interpretations, unsupported conclusions, limitations,
and suggested validation. Model output remains advisory. Tool names,
parameters, and workflow stages must pass local JSON Schema and rule checks.
The versioned context contract includes workflow order, current stage, available
inputs, summarized results, failed/skipped stages, artifacts and UI context. A new
module becomes AI-readable only after its structured output and registered tools
are added; the model still cannot read arbitrary local files or raw voltage.

Local Ollama
------------

Start Ollama separately, download a compatible model, and select the local
provider. The default compatible endpoint is
``http://127.0.0.1:11434/v1``. No cloud request is made in this mode.

.. warning::

   A configured provider does not grant permission to send project context.
   Every online request displays the outbound categories and requires user
   authorization.
