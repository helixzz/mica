"""Every value that may be written to SKUPriceRecord.source_type, in one place.

The API declared a Literal of four values, but five service functions inserted
records directly with their own strings — so the whitelist described a rule nothing
actually followed, and `supplier_quote` (still actively written by the PR quote
dialog) and `excel_import` were never in it.

Keeping the values here does not decide whether they should be merged; it only makes
"what can be written" a single fact instead of a guess.
"""

from __future__ import annotations

# Entered by hand on the price page.
MANUAL = "manual"
# A price quoted for an RFQ line.
QUOTE = "quote"
# The price actually paid on a purchase order.
ACTUAL_PO = "actual_po"
# Sourced from outside (competitor pricing, industry reports).
MARKET_RESEARCH = "market_research"
# A supplier's price for an item as saved from the PR line dialog. Still written.
SUPPLIER_QUOTE = "supplier_quote"
# Written by the admin Excel importer. Nothing in production yet.
EXCEL_IMPORT = "excel_import"
# Historical only: the old RFQ path inserted this directly and no longer does.
LEGACY_RFQ_QUOTE = "rfq_quote"

# What the API and the UI offer when a person records a price.
SELECTABLE = (MANUAL, QUOTE, ACTUAL_PO, MARKET_RESEARCH)

# Everything that may legitimately appear in the column, including rows the system
# wrote itself and rows written before the values were centralised.
ALL = (*SELECTABLE, SUPPLIER_QUOTE, EXCEL_IMPORT, LEGACY_RFQ_QUOTE)
