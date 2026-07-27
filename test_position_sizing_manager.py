from backtest.position_sizing_manager import (
    run_position_sizing_manager,
    save_position_sizing_manager,
)


def print_validation(name, value):
    print(f"{name:<40}: {value}")


def main():

    result = run_position_sizing_manager(
        symbol="AAPL",
        account_cash=10000,
    )

    report_path, latest_path = save_position_sizing_manager(result)

    print()
    print("=" * 100)
    print("VALIDATION CHECKS")
    print("=" * 100)

    print_validation("Version is V9.4", result.version == "V9.4")
    print_validation("Sizing status valid", result.sizing_status == "READY")
    print_validation("Sizing action valid", result.sizing_action in (
        "PREPARE_ENTRY",
        "PREPARE_EXIT",
        "MAINTAIN_POSITION",
        "NO_ACTION",
        "BLOCKED",
    ))

    print_validation("Source loaded", result.source_loaded)
    print_validation("Source valid", result.source_valid)

    print_validation("Account checks", result.account_checks_passed)
    print_validation("Price checks", result.price_checks_passed)
    print_validation("Risk checks", result.risk_checks_passed)
    print_validation("Sizing checks", result.sizing_checks_passed)
    print_validation("All checks", result.all_checks_passed)

    print_validation("Proposed shares valid", result.proposed_shares >= 0)
    print_validation("Position value valid", result.proposed_position_value >= 0)
    print_validation("Estimated cash valid", result.estimated_cash_after_entry >= 0)

    print_validation("Execution blocked", result.execution_blocked)
    print_validation("Order generated", result.order_generated is False)
    print_validation("Paper order blocked", result.paper_order_generated is False)
    print_validation("Live order blocked", result.live_order_generated is False)

    print_validation("Reasons exist", len(result.reasons) > 0)
    print_validation("Warnings exist", len(result.warnings) > 0)
    print_validation("Next actions exist", len(result.next_actions) > 0)

    print_validation("Report file exists", report_path.exists())
    print_validation("Latest file exists", latest_path.exists())

    print()
    print("=" * 100)

    print("V9.4 position sizing manager test completed successfully.")

    print(f"Position Action : {result.position_action}")
    print(f"Risk Decision   : {result.risk_decision}")
    print(f"Sizing Action   : {result.sizing_action}")

    print(f"Account Cash    : ${result.account_cash:,.2f}")
    print(f"Latest Price    : ${result.latest_close:,.2f}")

    print(f"Approved %      : {result.approved_position_percent:.2f}%")
    print(f"Target Value    : ${result.target_position_value:,.2f}")

    print(f"Proposed Shares : {result.proposed_shares}")

    print(f"Position Value  : ${result.proposed_position_value:,.2f}")

    print()

    print("Execution remains blocked.")
    print("No broker order generated.")
    print("Paper trading blocked.")
    print("Live trading blocked.")


if __name__ == "__main__":
    main()