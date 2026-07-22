from datetime import date

import boto3
from botocore.exceptions import ClientError


COST_EXPLORER_REGION = "us-east-1"


def get_current_month_dates():
    today = date.today()

    start_date = today.replace(day=1)

    # End date is exclusive, so using tomorrow includes today's cost data.
    end_date = date.fromordinal(today.toordinal() + 1)

    return start_date.isoformat(), end_date.isoformat()


def get_cost_by_service(cost_explorer, start_date, end_date):
    response = cost_explorer.get_cost_and_usage(
        TimePeriod={
            "Start": start_date,
            "End": end_date,
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[
            {
                "Type": "DIMENSION",
                "Key": "SERVICE",
            }
        ],
    )

    services = []

    for result in response.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            service_name = group["Keys"][0]

            amount = float(
                group["Metrics"]["UnblendedCost"]["Amount"]
            )

            services.append(
                {
                    "service": service_name,
                    "cost": amount,
                }
            )

    return services


def display_cost_report(services, start_date, end_date):
    print("\nAWS COST REPORT")
    print("-" * 75)
    print(f"Period: {start_date} to {end_date}")
    print("-" * 75)

    # Remove services with zero cost.
    paid_services = [
        service
        for service in services
        if service["cost"] > 0
    ]

    # Sort from highest cost to lowest cost.
    paid_services.sort(
        key=lambda service: service["cost"],
        reverse=True,
    )

    if not paid_services:
        print("No AWS costs found for this period.")
        return

    total_cost = 0

    for service in paid_services:
        total_cost += service["cost"]

        print(
            f"{service['service']:<55} "
            f"${service['cost']:>10.2f}"
        )

    print("-" * 75)
    print(f"{'Total cost':<55} ${total_cost:>10.2f}")


def main():
    cost_explorer = boto3.client(
        "ce",
        region_name=COST_EXPLORER_REGION,
    )

    start_date, end_date = get_current_month_dates()

    try:
        services = get_cost_by_service(
            cost_explorer,
            start_date,
            end_date,
        )

        display_cost_report(
            services,
            start_date,
            end_date,
        )

    except ClientError as error:
        details = error.response.get("Error", {})

        print(
            f"AWS error: "
            f"{details.get('Code')} - "
            f"{details.get('Message')}"
        )


if __name__ == "__main__":
    main()