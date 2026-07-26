from automation.auto_trainer import auto_train_symbol

result = auto_train_symbol("AAPL")

print()
print("=" * 70)
print("AUTO TRAIN RESULT")
print("=" * 70)

print("Symbol            :", result["symbol"])
print("Status            :", result["status"])
print("Started           :", result["started_at"])
print("Finished          :", result["finished_at"])
print("Elapsed           :", result["elapsed_seconds"], "sec")

print()

promotion = result["promotion_decision"]

print("Promotion decision :", promotion["decision"])
print("Should promote     :", promotion["should_promote"])
print("Candidate model    :", promotion["candidate_model"])
print("Candidate bal.acc. :", promotion["candidate_balanced_accuracy"])
print("Current model      :", promotion["current_model"])
print("Current bal.acc.   :", promotion["current_balanced_accuracy"])

print()

if result["backup_result"] is None:
    print("Backup : not required")
else:
    print("Backup created :",
          result["backup_result"]["backup_created"])

print()

if result["saved_model_info"] is None:
    print("Saved model : Current model retained")
else:
    print("Saved model :",
          result["saved_model_info"]["model_name"])

print()
print("V5 auto trainer test completed successfully.")