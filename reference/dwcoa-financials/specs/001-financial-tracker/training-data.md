# Training Data for Auto-Categorization

The file `DWCOA_Financials_24_v3.xlsx` in the project root contains ~400 already-categorized transactions from 2023-2024. This serves as training data for building the auto-categorization logic.

## How to Use This Data

### For the Rules Engine
Extract patterns from the `2023 Transactions` sheet:
- Map Description text patterns to Category assignments
- Examples:
  - "WASHINGTON ALARM" → "Fire Alarm"
  - "SEATTLEUTILTIES" or "SEATTLE CITY LIGHT" → "Seattle City Light"
  - "NWEDI-291390275 EDI" → "Insurance Premiums"
  - "J ERNAST" → "Dues 302" (specific homeowner)
  - "Dividend/Interest" → "Interest income"

### For the Claude API Prompt
Use representative examples from this data to craft few-shot examples in the categorization prompt.

### For Testing Accuracy
After building auto-categorization:
1. Take a subset of the categorized transactions
2. Remove categories
3. Run through the auto-categorization
4. Compare results to original categories
5. Target: 80%+ accuracy on recurring transaction types

## File Location

The Excel file should be copied to the project for reference:
- Source: Project files uploaded during spec development
- Contains sheets: Lookup, 2023 Transactions, Pivot, Financials 2024, Budget 2024

## Important Notes

- The treasurer will upload **uncategorized** CSV files in production
- This Excel file is for **training/reference only**, not for production data flow
- The production CSV format matches the columns in the "2023 Transactions" sheet
