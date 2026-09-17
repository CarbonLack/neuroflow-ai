Controlled AI assistant
=======================

Project-aware Harness conversations, readable answers, and Studies (v1.3.1)
----------------------------------------------------------------------------

For an institute-managed DeepSeek Harness account, use **Read local DeepSeek
Harness configuration** in AI settings. The Harness SDK route calls the installed
official dsh runtime; the app does not extract its model credentials or bypass it
with direct API requests. Install and configure Harness separately using
https://deepseek.com/harness/en/ .

Allow on-demand project data, results and conversation queries in the send preview.
The model can then query specific units, events, trials, spike times and result
tables through a local MCP interface, with evidence values and snapshot identifiers.
Try: “Query unit 25's SNR and ISI violation rate and explain the limitations.”
Chart metadata is not image-pixel access; raw voltage is not sent by this interface.

Conversations are saved to the project's ``ai/conversation.json`` and can be
searched after reopening it. Each request uses a fresh project snapshot. Switching
projects or provider settings requires renewed context approval. Analysis proposals
still require user confirmation and pass the existing application validators.
New analysis features require explicit tool registration; arbitrary shell, code
execution and file-system access are not granted.

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
