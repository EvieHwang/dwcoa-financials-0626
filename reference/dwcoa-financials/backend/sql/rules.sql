-- DWCOA Financial Tracker Categorization Rules
-- Simple case-insensitive substring matching rules for auto-categorization
-- Rules are matched by priority (higher = checked first), then by pattern length (longer = more specific)

-- Clear existing rules (for clean re-initialization)
DELETE FROM categorize_rules;

-- Expense categories
INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'BULGER SAFE', id, 100, 100, 1 FROM categories WHERE name = 'Bulger Safe & Lock';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'Cintas', id, 100, 100, 1 FROM categories WHERE name = 'Cintas Fire Protection';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT '309 S CLOVERDALE ST', id, 100, 100, 1 FROM categories WHERE name = 'Common Area Cleaning';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'CENTURYLINK', id, 100, 100, 1 FROM categories WHERE name = 'Fire Alarm';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'LumenCenturyLink', id, 100, 100, 1 FROM categories WHERE name = 'Fire Alarm';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'WASHINGTON ALARM', id, 100, 100, 1 FROM categories WHERE name = 'Fire Alarm';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'MCCARY', id, 100, 100, 1 FROM categories WHERE name = 'Grounds/Landscaping';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'NWEDI-291390275', id, 100, 100, 1 FROM categories WHERE name = 'Insurance Premiums';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'SEATTLEUTILTIES', id, 100, 100, 1 FROM categories WHERE name = 'Seattle City Light';

-- Interest income
INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'Dividend/Interest', id, 100, 100, 1 FROM categories WHERE name = 'Interest income';

-- Dues by unit (using distinctive patterns that won't conflict)
INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'BOEING EMPLOYEES CREDIT UNION', id, 100, 100, 1 FROM categories WHERE name = 'Dues 101';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'Emma Landsman', id, 100, 100, 1 FROM categories WHERE name = 'Dues 102';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'JARED MOLTON', id, 100, 100, 1 FROM categories WHERE name = 'Dues 103';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'EVE HWANG ONLNE', id, 100, 100, 1 FROM categories WHERE name = 'Dues 201';

-- NOTE: Dues 202 'Deposit' pattern removed - too generic, conflicts with other deposits
-- Unit 202 deposits will be flagged for review. Add a more specific pattern via Manage Rules.

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'WENLU CHENG', id, 100, 100, 1 FROM categories WHERE name = 'Dues 203';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'R Young ACH', id, 100, 100, 1 FROM categories WHERE name = 'Dues 301';

-- Fixed: Using ERNAST without prefix to match both "J ERNAST" and "J_Ernast" variations
INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'ERNAST', id, 100, 100, 1 FROM categories WHERE name = 'Dues 302';

INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
SELECT 'Business Mobile Deposit', id, 100, 100, 1 FROM categories WHERE name = 'Dues 303';

-- Note: Internal transfers are handled by code logic (description contains 'Transfer' AND account number)
-- Anything that doesn't match a rule will be flagged for review
