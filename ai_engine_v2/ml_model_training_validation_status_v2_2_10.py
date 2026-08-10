def build_v2_2_10_status():
    return {
        "stage":"AI_TRADING_ENGINE_V2_2_10_ML_MODEL_TRAINING_VALIDATION",
        "status":"PASS_DEVELOPMENT_COMPLETE",
        "isolated_ml_venv":True,
        "candidate_models":[
            "dummy_prior",
            "logistic_balanced",
            "hist_gradient_boosting",
        ],
        "validation_only_model_selection":True,
        "test_used_for_selection":False,
        "test_evaluated_after_selection":True,
        "bounded_walk_forward":True,
        "walk_forward_embargo_market_dates":1,
        "train_row_cap":250000,
        "horizons":[5,15,30,60],
        "automatic_promotion":False,
        "execution_selector_modified":False,
        "broker_network":False,
        "orders":0,
        "live_trading":False,
    }
