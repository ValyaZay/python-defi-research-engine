
import json
from scripts.asset_to_price_feed import asset_to_feed

def getPriceAndRoundId(asset, timestamp):
    priceFeed = asset_to_feed[asset]

    last_valid = None

    with open(f"aggregatorsRoundData/{priceFeed}.jsonl") as f:
        for line in f:
            obj = json.loads(line)

            if obj["updatedAt"] < timestamp:
                last_valid = obj
            else:
                break   # because data is chronological

    if not last_valid:
        return None
    
    return last_valid["answer"], last_valid["roundId"]

if __name__ == '__main__':
    asset = "0x6B175474E89094C44Da98b954EedeAC495271d0F" #dai
    (answer, round_id) = getPriceAndRoundId(asset, 1754078193)
    print(answer)
    print(round_id)