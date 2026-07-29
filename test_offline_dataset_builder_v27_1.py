
import backtest.offline_dataset_builder_v27_1 as m
rows=[{"features":[1,2,3],"label":1},{"features":[4,5,6],"label":0}]
ds=m.build_dataset(rows)
checks=[
("V27.1 version",ds["version"]=="27.1"),
("Dataset built",len(ds["samples"])==2),
("Hash verified",m.verify(ds)),
("Market blocked",not m.MARKET_DATA_API_CALLED),
("Network blocked",not m.NETWORK_ACCESSED),
("Broker blocked",not m.BROKER_API_CALLED),
("Order blocked",not m.ORDER_SUBMITTED),
("Live blocked",not m.LIVE_EXECUTION_AUTHORIZED),
]
for n,c in checks:
    print(f"{n:<40}: {c}")
    assert c
print("V27.1 offline dataset builder completed successfully.")
