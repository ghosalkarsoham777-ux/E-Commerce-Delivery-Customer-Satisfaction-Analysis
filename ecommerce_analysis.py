"""
E-Commerce Delivery & Customer Satisfaction Intelligence
End-to-end data analytics project using the Olist Brazilian e-commerce datasets.

Run from the project root:
    python ecommerce_analysis.py

Outputs are saved in outputs/ and reports/.
"""
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore", category=FutureWarning)
sns.set_theme(style="whitegrid")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "dataset" / "dataset"
OUT = ROOT / "outputs"
REPORTS = ROOT / "reports"
OUT.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

def load_csv(name):
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing dataset: {path}\n"
            "Keep the CSV files inside data/dataset/dataset/."
        )
    return pd.read_csv(path)

def save_chart(filename):
    plt.tight_layout()
    plt.savefig(OUT / filename, dpi=250, bbox_inches="tight")
    plt.close()

def main():
    print("=" * 65)
    print("E-COMMERCE DELIVERY & CUSTOMER SATISFACTION INTELLIGENCE")
    print("=" * 65)

    orders = load_csv("olist_orders_dataset.csv")
    reviews = load_csv("olist_order_reviews_dataset.csv")
    customers = load_csv("olist_customers_dataset.csv")
    items = load_csv("olist_order_items_dataset.csv")
    products = load_csv("olist_products_dataset.csv")
    payments = load_csv("olist_order_payments_dataset.csv")
    sellers = load_csv("olist_sellers_dataset.csv")
    categories = load_csv("product_category_name_translation.csv")

    # 1. Initial data quality profile
    datasets = {
        "orders": orders, "reviews": reviews, "customers": customers,
        "items": items, "products": products, "payments": payments,
        "sellers": sellers, "categories": categories
    }
    quality_rows = []
    for name, df in datasets.items():
        quality_rows.append({
            "dataset": name,
            "rows": len(df),
            "columns": len(df.columns),
            "duplicate_rows": int(df.duplicated().sum()),
            "missing_cells": int(df.isna().sum().sum())
        })
    quality = pd.DataFrame(quality_rows)
    quality.to_csv(OUT / "data_quality_summary.csv", index=False)
    print("\nDATASET PROFILE")
    print(quality.to_string(index=False))

    # 2. Parse dates and create delivery metrics
    date_cols = [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ]
    for col in date_cols:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")

    delivered = orders.loc[
        (orders["order_status"] == "delivered")
        & orders["order_delivered_customer_date"].notna()
        & orders["order_purchase_timestamp"].notna()
        & orders["order_estimated_delivery_date"].notna()
    ].copy()

    delivered["delivery_days"] = (
        delivered["order_delivered_customer_date"] -
        delivered["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400

    delivered["delay_days"] = (
        delivered["order_delivered_customer_date"] -
        delivered["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400

    delivered["delivery_status"] = np.where(
        delivered["delay_days"] > 0, "Late", "On Time / Early"
    )
    delivered["delay_group"] = pd.cut(
        delivered["delay_days"],
        bins=[-np.inf, 0, 3, 7, 14, np.inf],
        labels=["On Time / Early", "1-3 days", "4-7 days", "8-14 days", "15+ days"]
    )

    # 3. Customer reviews: average score per order prevents repeated review rows
    review_summary = reviews.groupby("order_id", as_index=False).agg(
        review_score=("review_score", "mean"),
        review_count=("review_id", "nunique")
    )
    satisfaction = delivered.merge(review_summary, on="order_id", how="left")
    satisfaction.to_csv(OUT / "delivery_satisfaction_detail.csv", index=False)

    # 4. Business KPIs
    total_orders = int(orders["order_id"].nunique())
    delivered_count = int(delivered["order_id"].nunique())
    late_count = int((delivered["delay_days"] > 0).sum())
    ontime_count = int((delivered["delay_days"] <= 0).sum())
    late_pct = float((delivered["delay_days"] > 0).mean() * 100) if len(delivered) else np.nan
    avg_delivery = float(delivered["delivery_days"].mean()) if len(delivered) else np.nan
    avg_review = float(reviews["review_score"].mean())
    total_sales = float(items["price"].sum())
    total_freight = float(items["freight_value"].sum())
    payment_total = float(payments["payment_value"].sum())

    kpis = pd.DataFrame([
        ["Unique orders", total_orders, "count"],
        ["Delivered orders with valid dates", delivered_count, "count"],
        ["Late delivered orders", late_count, "count"],
        ["On-time or early delivered orders", ontime_count, "count"],
        ["Late delivery rate", round(late_pct, 2), "%"],
        ["Average delivery time", round(avg_delivery, 2), "days"],
        ["Average review score", round(avg_review, 2), "out of 5"],
        ["Item sales value", round(total_sales, 2), "dataset currency units"],
        ["Freight value", round(total_freight, 2), "dataset currency units"],
        ["Payment value", round(payment_total, 2), "dataset currency units"],
    ], columns=["metric", "value", "unit"])
    kpis.to_csv(OUT / "business_kpis.csv", index=False)
    print("\nBUSINESS KPIs")
    print(kpis.to_string(index=False))

    # 5. Delivery status and satisfaction comparison
    rating_by_status = satisfaction.groupby("delivery_status", dropna=False).agg(
        orders=("order_id", "nunique"),
        average_review=("review_score", "mean"),
        median_delay_days=("delay_days", "median")
    ).round(2).reset_index()
    rating_by_status.to_csv(OUT / "satisfaction_by_delivery_status.csv", index=False)
    print("\nSATISFACTION BY DELIVERY STATUS")
    print(rating_by_status.to_string(index=False))

    # 6. Monthly order trend
    orders["order_month"] = orders["order_purchase_timestamp"].dt.to_period("M").astype("string")
    monthly = orders.dropna(subset=["order_month"]).groupby("order_month").agg(
        orders=("order_id", "nunique")
    ).reset_index()
    monthly.to_csv(OUT / "monthly_order_trend.csv", index=False)
    plt.figure(figsize=(12, 5))
    sns.lineplot(data=monthly, x="order_month", y="orders", marker="o")
    plt.title("Monthly Order Trend")
    plt.xlabel("Month")
    plt.ylabel("Unique Orders")
    plt.xticks(rotation=45)
    save_chart("monthly_order_trend.png")

    # 7. Review score distribution
    review_counts = reviews["review_score"].value_counts().sort_index().rename_axis("review_score").reset_index(name="reviews")
    review_counts.to_csv(OUT / "review_score_distribution.csv", index=False)
    plt.figure(figsize=(8, 5))
    sns.barplot(data=review_counts, x="review_score", y="reviews", color="#287D8E")
    plt.title("Customer Review Score Distribution")
    plt.xlabel("Review Score (1-5)")
    plt.ylabel("Number of Reviews")
    save_chart("review_score_distribution.png")

    # 8. Delivery delay distribution (late orders only)
    late = delivered.loc[delivered["delay_days"] > 0].copy()
    late["delay_group"] = pd.cut(
        late["delay_days"], bins=[0, 3, 7, 14, np.inf],
        labels=["1-3 days", "4-7 days", "8-14 days", "15+ days"],
        include_lowest=True
    )
    delay_counts = late["delay_group"].value_counts(sort=False).rename_axis("delay_group").reset_index(name="orders")
    delay_counts.to_csv(OUT / "delivery_delay_distribution.csv", index=False)
    plt.figure(figsize=(9, 5))
    sns.barplot(data=delay_counts, x="delay_group", y="orders", color="#D17A42")
    plt.title("Distribution of Late Delivery Duration")
    plt.xlabel("Delay Duration")
    plt.ylabel("Number of Orders")
    save_chart("delivery_delay_distribution.png")

    # 9. Product category analysis with English translation
    product_data = items.merge(products, on="product_id", how="left")
    product_data = product_data.merge(categories, on="product_category_name", how="left")
    product_data = product_data.merge(review_summary[["order_id", "review_score"]], on="order_id", how="left")
    product_data["category"] = product_data["product_category_name_english"].fillna(
        product_data["product_category_name"]
    ).fillna("unknown")
    category = product_data.groupby("category", as_index=False).agg(
        item_count=("order_id", "count"),
        sales_value=("price", "sum"),
        average_review=("review_score", "mean")
    )
    category["average_review"] = category["average_review"].round(2)
    category["sales_value"] = category["sales_value"].round(2)
    category.sort_values("sales_value", ascending=False).to_csv(OUT / "category_performance.csv", index=False)

    lowest = category.dropna(subset=["average_review"]).nsmallest(10, "average_review").sort_values("average_review")
    lowest.to_csv(OUT / "lowest_rated_categories.csv", index=False)
    plt.figure(figsize=(11, 6))
    sns.barplot(data=lowest, x="average_review", y="category", color="#4C8C72")
    plt.title("10 Lowest-Rated Product Categories")
    plt.xlabel("Average Review Score")
    plt.ylabel("Product Category")
    save_chart("lowest_rated_categories.png")

    # 10. State-wise delivery performance
    state_data = delivered.merge(customers[["customer_id", "customer_state"]], on="customer_id", how="left")
    state_summary = state_data.dropna(subset=["customer_state"]).groupby("customer_state").agg(
        delivered_orders=("order_id", "nunique"),
        late_delivery_percentage=("delay_days", lambda s: (s > 0).mean() * 100),
        average_delay_days=("delay_days", "mean")
    ).reset_index()
    state_summary[["late_delivery_percentage", "average_delay_days"]] = state_summary[
        ["late_delivery_percentage", "average_delay_days"]
    ].round(2)
    state_summary.sort_values("late_delivery_percentage", ascending=False).to_csv(
        OUT / "state_delivery_performance.csv", index=False
    )
    state_plot = state_summary.nlargest(10, "late_delivery_percentage").sort_values("late_delivery_percentage")
    plt.figure(figsize=(10, 6))
    sns.barplot(data=state_plot, x="late_delivery_percentage", y="customer_state", color="#477DA8")
    plt.title("Top 10 States by Late Delivery Percentage")
    plt.xlabel("Late Delivery Percentage (%)")
    plt.ylabel("Customer State")
    save_chart("state_delivery_performance.png")

    # 11. Payment method analysis
    payment_summary = payments.groupby("payment_type", as_index=False).agg(
        transactions=("order_id", "count"),
        total_payment=("payment_value", "sum"),
        average_payment=("payment_value", "mean")
    )
    payment_summary[["total_payment", "average_payment"]] = payment_summary[
        ["total_payment", "average_payment"]
    ].round(2)
    payment_summary.sort_values("total_payment", ascending=False).to_csv(
        OUT / "payment_method_analysis.csv", index=False
    )

    # 12. Seller performance
    seller_items = items.merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")
    seller_summary = seller_items.groupby("seller_id", as_index=False).agg(
        items_sold=("order_id", "count"),
        sales_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
        seller_state=("seller_state", "first")
    )
    seller_summary.sort_values("sales_value", ascending=False).head(20).to_csv(
        OUT / "top_20_sellers_by_sales.csv", index=False
    )

    # 13. Data validation results
    validation = pd.DataFrame([
        ["Duplicate order IDs in orders", int(orders["order_id"].duplicated().sum())],
        ["Review scores outside 1-5", int((~reviews["review_score"].between(1, 5)).sum())],
        ["Negative delivery durations", int((delivered["delivery_days"] < 0).sum())],
        ["Delivered orders used in delay analysis", len(delivered)],
        ["Late orders", late_count],
        ["On-time or early orders", ontime_count],
        ["Delivery totals reconcile", bool(len(delivered) == late_count + ontime_count)]
    ], columns=["check", "result"])
    validation.to_csv(OUT / "data_validation.csv", index=False)

    # 14. Auto-generated business summary; values are calculated from the loaded files.
    top_category = category.sort_values("sales_value", ascending=False).head(1)
    lowest_category = category.dropna(subset=["average_review"]).sort_values("average_review").head(1)
    top_state = state_summary.sort_values("late_delivery_percentage", ascending=False).head(1)
    lines = [
        "# E-Commerce Analytics — Business Findings",
        "",
        "## KPI snapshot",
        f"- Unique orders: {total_orders:,}",
        f"- Delivered orders with valid dates: {delivered_count:,}",
        f"- Late delivery rate among delivered orders with valid dates: {late_pct:.2f}%",
        f"- Average delivery time: {avg_delivery:.2f} days",
        f"- Average review score across review records: {avg_review:.2f}/5",
        f"- Item sales value (sum of item prices): {total_sales:,.2f}",
        "",
        "## Findings to investigate",
    ]
    if not top_category.empty:
        lines.append(f"- Highest item sales category in this dataset: **{top_category.iloc[0]['category']}** ({top_category.iloc[0]['sales_value']:,.2f}).")
    if not lowest_category.empty:
        lines.append(f"- Lowest-rated category among categories with review data: **{lowest_category.iloc[0]['category']}** ({lowest_category.iloc[0]['average_review']:.2f}/5).")
    if not top_state.empty:
        lines.append(f"- Highest late-delivery percentage among states in the delivered-order sample: **{top_state.iloc[0]['customer_state']}** ({top_state.iloc[0]['late_delivery_percentage']:.2f}%). Check its order count before drawing conclusions.")
    lines += [
        "",
        "## Recommendations",
        "1. Investigate the operational causes of late deliveries in the states with the highest late-delivery rates, while checking sample sizes.",
        "2. Review low-rated product categories and examine product descriptions, seller quality, packaging, and delivery experience.",
        "3. Monitor monthly order volume and plan fulfilment capacity around high-volume periods.",
        "4. Treat missing timestamps carefully; delivery KPIs use only orders with valid purchase, delivery, and estimated delivery timestamps.",
        "5. Interpret item price totals and payment totals separately: payments may include installments, freight, and other payment-record effects.",
        "",
        "## Data caveats",
        "- This project uses the supplied Olist CSV datasets; it does not establish causation.",
        "- Review records may contain missing comments; a missing comment is not the same as a missing score.",
        "- Geolocation has over one million rows and repeated postal-code-level coordinates; duplicates should be evaluated by use case rather than removed blindly.",
        "- Currency values are kept in the source dataset's currency units.",
    ]
    (REPORTS / "business_findings.md").write_text("\n".join(lines), encoding="utf-8")

    print("\nProject run completed.")
    print(f"Charts and CSV outputs: {OUT}")
    print(f"Business findings report: {REPORTS / 'business_findings.md'}")
    print("Open outputs/ and reports/ to review the generated results.")

if __name__ == "__main__":
    main()
