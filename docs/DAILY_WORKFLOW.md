# Daily Workflow

This document outlines a standard daily workflow using the Mythic interactive companion shell.

## 1. Start the Day

Navigate to your project repository and launch Mythic:
```bash
mythic
```
You will be greeted with a status banner confirming your branch, LLM provider, and active memory store.

## 2. Re-orient

Ask Mythic to recall your previous session:
> "What were we working on yesterday?"

Mythic will read the `.mythic/memory.sqlite` spine and summarize the last known state, failures, and pending next steps.

## 3. Discuss the Task

Explain what you want to achieve:
> "Let's fix the bug in the authentication module where tokens expire prematurely."

Mythic will inspect the repo, locate the authentication module, and load it into context.

## 4. Review and Apply Patches

Mythic will propose a patch to fix the issue. You can review the changes:
```bash
/diff
```
If the code looks correct, approve and apply it:
```bash
/apply
```

## 5. Verify

Run the test suite through Mythic:
```bash
/test
```
If tests fail, Mythic will automatically ingest the failure output and propose a subsequent fix.

## 6. Commit and Reflect

Once satisfied, ask Mythic to commit:
> "Commit these changes."

Mythic will draft a semantic commit message, request approval, and execute the commit. The session details and decisions will be written back to the memory spine, ready for tomorrow.\n