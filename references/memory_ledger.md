# Working-Directory Episodic Memory System (`astra_memory.md`)

## Rationale & Operating Principles

### Why Memory Must Live in the Working Directory
The agent must **never** store task logs inside the central `skills/` directory. Instead, the task journal `astra_memory.md` must strictly reside in the **current working directory (CWD)** where the agent was invoked:
- It isolates task-specific state to the project at hand.
- It prevents collisions between different projects or user workflows.
- It provides git-versionable documentation of automated actions.

### The 50-Screenshot Pruning Challenge
The screen perception daemon enforces a strict **50-screenshot rolling FIFO buffer** in `screenshots/history/`. Once 50 screenshots are captured (approx. 100 seconds of activity), older frames are permanently deleted to conserve disk storage.

**Consequence**: The AI agent cannot rely on looking back at past screenshots to remember:
- What text was shown on previous web pages or dialogues.
- Which navigation steps were already attempted.
- Why a particular click failed 3 minutes ago.
- Temporary verification tokens, order numbers, or form fields.

**Solution**: The working-directory `astra_memory.md` serves as the agent's durable brain. Every critical piece of information, navigation hurdle, and bug resolution MUST be written to `astra_memory.md` immediately upon observation.

---

## Structure of `astra_memory.md`

Every `astra_memory.md` must follow this standard format:

```markdown
# GPT-6 Astra Task Memory & Screen Journal

**Initialized:** 2026-09-08 14:00:00  
**Working Directory:** `/path/to/project`  
**Primary Goal:** [Full User Request]

---

## Task Overview & Progress State
- **Status:** In Progress | Completed | Blocked
- **Current Subgoal:** [e.g., Fill payment form]
- **Total Screens Observed:** [Count]
- **Actions Executed:** [Count]

---

## Critical Extracted Information & Entity Vault
> Permanent store for text, credentials, confirmation IDs, form fields, and data
> extracted from screenshots that are needed later in the task.

- **Invoice ID:** `INV-90218` (Screen 3)
- **Email Entered:** `user@example.com` (Screen 7)
- **Token:** `xyz-4491` (Screen 12)

---

## Navigation Obstacles, UI Quirks & Resolution Log
> Detailed record of navigation hurdles, misclicks, unresponsive elements, or unexpected
> popups, along with the exact coordinates and remedies used to overcome them.

- **Issue at 'Checkout Modal':** Primary click at `(650, 420)` hit invisible backdrop overlay.
  - **Fix:** Used double-click at `(660, 425)` after scrolling down 200px.
- **Issue at 'Login Dropdown':** Dropdown closed immediately on hover.
  - **Fix:** Executed `click --x 340 --y 120` without hover first.

---

## Chronological Screen Observation & Action Log

### [Screen Event] - 2026-09-08 14:02:15
- **Screen / View Title:** Checkout Page - Step 2
- **Visual Observations:** Shipping address form displayed. 'Continue to Payment' button is blue at bottom right.
- **Extracted Information:** Total amount: $128.50. Shipping: Free.
- **Action Taken:** `click` at coordinates `(820, 680)`
- **Outcome / Visual Feedback:** Spinner appeared, transitioning to Payment step.
```

---

## Automatic vs. Direct Updates

The agent can update `astra_memory.md` via two methods:
1. **Helper CLI (`memory_manager.py`)**:
   ```bash
   python3 <skill_dir>/scripts/memory_manager.py log \
     --title "Checkout Page" \
     --observation "Form filled with details" \
     --action "click" --x 820 --y 680 \
     --extracted "Order total: $128.50" \
     --outcome "Moved to payment step"
   ```
2. **Direct File Editing**:
   Using `replace_file_content` to update the Entity Vault or add custom notes.
