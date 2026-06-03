# Transaction Categorization Feature

## Overview

This feature provides a semi-automated workflow for categorizing financial transactions. New transactions are automatically categorized when they match predefined text patterns, while unmatched transactions are flagged for manual review. The system learns from manual categorizations by allowing users to create new rules on the fly.

---

## Core Components

### 1. Categories

A list of named categories that transactions can be assigned to (e.g., "Utilities", "Insurance", "Dues - Unit 201"). Each category has a name, type (Income/Expense/Transfer), and can be marked active or inactive.

### 2. Categorization Rules

Each rule consists of:

- **Pattern**: A text string to match against transaction descriptions (case-insensitive substring matching)
- **Target Category**: The category to assign when the pattern matches
- **Priority**: Higher priority rules are checked first, allowing specific patterns to override general ones
- **Active Flag**: Rules can be disabled without deleting them

### 3. Transactions

Each transaction stores:

- The assigned category (if any)
- A "needs review" flag indicating whether it requires human attention

---

## Workflow

### Phase 1: Upload and Auto-Categorization

When new transactions are uploaded (typically via CSV):

1. Each transaction's description is checked against all active rules
2. Rules are evaluated in priority order; the first matching pattern wins
3. **If a rule matches**: The transaction is assigned that category with high confidence and marked as "does not need review"
4. **If no rule matches**: The transaction is left uncategorized and flagged with "needs review = true"
5. After processing, the system reports statistics: how many were auto-categorized vs. how many need review

### Phase 2: Review Queue

The application displays a count of transactions needing review (e.g., "Review Transactions (5)").

When the user opens the review queue:

- They see a list of all uncategorized transactions
- Each item shows the description, date, amount, and account
- For each transaction, the user has two options:

**Option A: Simple Categorization**

- Select a category from a dropdown
- Click "Save"
- The transaction is categorized and removed from the review queue

**Option B: Create a Rule**

- Select a category
- Click "Create Rule"
- An inline form appears with the transaction description pre-filled as the pattern
- The user can edit the pattern to make it more general (e.g., changing "SEATTLE UTILITIES BILL 12345" to just "SEATTLE UTILITIES")
- Upon saving, the rule is created AND the current transaction is categorized

### Phase 3: Rule Management

A separate interface allows users to:

- View all existing rules with their patterns and target categories
- Edit patterns or change the target category
- Delete or disable rules that are no longer needed
- Create new rules manually (without going through the review queue)

---

## Key Design Decisions

### Substring Matching (Not Regex)

Patterns use simple case-insensitive substring matching. If the pattern "ELECTRIC" is defined, it matches any description containing that word (e.g., "PUGET SOUND ELECTRIC COMPANY"). This is easier for non-technical users to understand and manage.

### No Retroactive Application

When a new rule is created, it does **not** automatically re-categorize existing transactions. This preserves the integrity of historical data and prevents unexpected changes. Rules only affect newly uploaded transactions.

### Proactive Application

Every new upload triggers the full categorization engine. New rules immediately apply to fresh transactions without any additional configuration.

### Priority System

When multiple rules could match the same transaction, the one with higher priority wins. This allows both general rules (e.g., "BANK" → Transfers) and specific overrides (e.g., "BANK OF AMERICA INTEREST" → Interest Income).

### Learn as You Go

The workflow encourages building the rule set incrementally. Initially, many transactions need manual review. As users create rules from those reviews, future uploads become increasingly automated.

---

## User Experience Flow

```
┌─────────────────────────────────────────────────────────┐
│  UPLOAD TRANSACTIONS                                     │
│  ─────────────────────                                   │
│  User uploads CSV file                                   │
│       ↓                                                  │
│  System auto-categorizes using existing rules            │
│       ↓                                                  │
│  Result: "150 added, 145 categorized, 5 need review"    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  REVIEW QUEUE                                            │
│  ────────────                                            │
│  Badge shows: "Review Transactions (5)"                  │
│       ↓                                                  │
│  User opens queue, sees uncategorized items              │
│       ↓                                                  │
│  For each item:                                          │
│    • Select category → Save (one-time fix)               │
│    • Select category → Create Rule (permanent fix)       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  NEXT UPLOAD                                             │
│  ───────────                                             │
│  New rules now catch transactions automatically          │
│  Fewer items in review queue over time                   │
└─────────────────────────────────────────────────────────┘
```

---

## Summary for Implementation

To implement this feature, you need:

1. **Categories table**: Name, type, active status
2. **Rules table**: Pattern string, linked category, priority, active status
3. **Transactions table**: Fields for category assignment, needs_review flag, and confidence
4. **Categorization service**: Loops through active rules (by priority), performs substring matching, returns match or "needs review"
5. **Upload handler**: Processes each transaction through the categorization service
6. **Review queue UI**: Lists flagged transactions with category selection and rule creation options
7. **Rules management UI**: CRUD interface for viewing/editing/deleting rules

The key insight is that this creates a **feedback loop**: manual categorizations can become rules, which reduce future manual work. The system becomes more automated over time as users teach it their categorization preferences.
