# E-Commerce Analytics — Business Findings

## KPI snapshot
- Unique orders: 99,441
- Delivered orders with valid dates: 96,470
- Late delivery rate among delivered orders with valid dates: 8.11%
- Average delivery time: 12.56 days
- Average review score across review records: 4.09/5
- Item sales value (sum of item prices): 13,591,643.70

## Findings to investigate
- Highest item sales category in this dataset: **health_beauty** (1,258,681.34).
- Lowest-rated category among categories with review data: **security_and_services** (2.50/5).
- Highest late-delivery percentage among states in the delivered-order sample: **AL** (23.93%). Check its order count before drawing conclusions.

## Recommendations
1. Investigate the operational causes of late deliveries in the states with the highest late-delivery rates, while checking sample sizes.
2. Review low-rated product categories and examine product descriptions, seller quality, packaging, and delivery experience.
3. Monitor monthly order volume and plan fulfilment capacity around high-volume periods.
4. Treat missing timestamps carefully; delivery KPIs use only orders with valid purchase, delivery, and estimated delivery timestamps.
5. Interpret item price totals and payment totals separately: payments may include installments, freight, and other payment-record effects.

## Data caveats
- This project uses the supplied Olist CSV datasets; it does not establish causation.
- Review records may contain missing comments; a missing comment is not the same as a missing score.
- Geolocation has over one million rows and repeated postal-code-level coordinates; duplicates should be evaluated by use case rather than removed blindly.
- Currency values are kept in the source dataset's currency units.