Controlled AI assistant
=======================

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

This is a native provider adapter, not UI automation of the Harness website.
Harness supplies model access; NeuroEphys AI owns the versioned project context,
tool validation, scientific constraints, audit trail, and user confirmation.

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
