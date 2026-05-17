# FAQ

## Is this a chatbot?

No. It is a small boundary-control reference project. It does not include a model backend, chat UI, memory database, or hosted service.

## Does this include private memory or personal data?

No. The public tree contains generalized source, tests, examples, and documentation only.

## Can I connect it to my own agent?

Yes. Call the modules before your own model call, background job, or optional agent-initiated message. You decide where state is stored and which model or tool layer is used.

## Does it require an API key?

No. The included tests and demo do not call external APIs. If your own integration uses an external model or search API, keep those credentials outside this repository.

## Why not include a full web UI?

The goal of this snapshot is to keep the behavior-boundary layer inspectable. A UI can be built separately around these modules.

## What should I read first?

Read `README.md`, then `docs/GETTING_STARTED.md`, then `docs/RUNTIME_BOUNDARIES.md`.
