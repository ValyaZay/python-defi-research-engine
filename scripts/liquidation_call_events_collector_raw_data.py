from web3 import Web3
from dotenv import load_dotenv
import os
from solcx import install_solc
install_solc(version='latest')

load_dotenv()
URL_MAINNET_ETHEREUM = os.getenv("URL_MAINNET_ETHEREUM")
w3 = Web3(Web3.HTTPProvider(URL_MAINNET_ETHEREUM))
print("Connected:", w3.is_connected())

POOL_ADDRESS="0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2" # from https://aave.com/docs/resources/addresses
POOL_ABI=[{
            "type": "event",
            "name": "LiquidationCall",
            "inputs": [
                {
                    "name": "collateralAsset",
                    "type": "address",
                    "indexed": True,
                    "internalType": "address"
                },
                {
                    "name": "debtAsset",
                    "type": "address",
                    "indexed": True,
                    "internalType": "address"
                },
                {
                    "name": "user",
                    "type": "address",
                    "indexed": True,
                    "internalType": "address"
                },
                {
                    "name": "debtToCover",
                    "type": "uint256",
                    "indexed": False,
                    "internalType": "uint256"
                },
                {
                    "name": "liquidatedCollateralAmount",
                    "type": "uint256",
                    "indexed": False,
                    "internalType": "uint256"
                },
                {
                    "name": "liquidator",
                    "type": "address",
                    "indexed": False,
                    "internalType": "address"
                },
                {
                    "name": "receiveAToken",
                    "type": "bool",
                    "indexed": False,
                    "internalType": "bool"
                }
            ],
            "anonymous": False
        },
        {
            "type": "event",
            "name": "Repay",
            "inputs": [
                {
                    "name": "reserve",
                    "type": "address",
                    "indexed": True,
                    "internalType": "address"
                },
                {
                    "name": "user",
                    "type": "address",
                    "indexed": True,
                    "internalType": "address"
                },
                {
                    "name": "repayer",
                    "type": "address",
                    "indexed": True,
                    "internalType": "address"
                },
                {
                    "name": "amount",
                    "type": "uint256",
                    "indexed": False,
                    "internalType": "uint256"
                },
                {
                    "name": "useATokens",
                    "type": "bool",
                    "indexed": False,
                    "internalType": "bool"
                }
            ],
            "anonymous": False
        }
        ]
POOL_CONTRACT = w3.eth.contract(address=POOL_ADDRESS, abi=POOL_ABI)
# ORACLE_ADDRESS="0x54586bE62E3c3580375aE3723C145253060Ca0C2" # from https://aave.com/docs/resources/addresses
# ORACLE_ABI=[{
        #     "type": "function",
        #     "name": "getAssetPrice",
        #     "inputs": [
        #         {
        #             "name": "asset",
        #             "type": "address",
        #             "internalType": "address"
        #         }
        #     ],
        #     "outputs": [
        #         {
        #             "name": "",
        #             "type": "uint256",
        #             "internalType": "uint256"
        #         }
        #     ],
        #     "stateMutability": "view"
        # }]

ERC20_ABI=[{
            "type": "function",
            "name": "decimals",
            "inputs": [],
            "outputs": [
                {
                    "name": "",
                    "type": "uint8",
                    "internalType": "uint8"
                }
            ],
            "stateMutability": "view"
        }]


############################################################

def collect_round_data_for_range(asset_address, start, end):
    AGGREGATOR_CONTRACT = get_aggregator_contract(asset_address)
    chunk_size = 100
    filename = f"aggregatorsRoundData/{AGGREGATOR_CONTRACT.address}.jsonl"

    roundData = []
    for round_id in range(start, end + 1):# end + 1 to include end roundId
        try:
            data = AGGREGATOR_CONTRACT.functions.getRoundData(round_id).call()
            if(data[1] == 0):
                print("Zero answer encountered. Stopping.")
                break

            roundDataItem = {
                "roundId": data[0],
                "answer": data[1],
                "startedAt": data[2],
                "updatedAt": data[3]
            }
            
            print(f"Round {round_id}: {data}")

            roundData.append(roundDataItem)
            round_id += 1

            # When chunk full → flush to disk
            if len(roundData) >= chunk_size:
                with open(filename, "a") as f:
                    for obj in roundData:
                        f.write(json.dumps(obj) + "\n")
                roundData.clear()
            
            time.sleep(0.05)

        except ContractLogicError:
            print(f"Reverted at round {round_id}. Stopping.")
            break
    # Flush remaining items
    if roundData:
        with open(filename, "a") as f:
            for obj in roundData:
                f.write(json.dumps(obj) + "\n")
    
    print("Finished to collect data.")

def get_last_saved_round(filename):
    try:
        with open(filename, "rb") as f:
            f.seek(-1024, 2)  # read last KB
            lines = f.readlines()
            last_line = lines[-1].decode()
            return json.loads(last_line)["roundId"]
    except:
        return None
    
def collect_round_data(asset_address):
    filename = f"events_data/liquidation_call_events_raw_data.jsonl"

    latest_round_data = AGGREGATOR_CONTRACT.functions.latestRoundData().call()
    print('latest_round_id ', latest_round_data[0])
    last_collected_block = get_last_saved_block(filename)
    print('last_collected_block ', last_collected_block)
    if last_collected_block is None:
        last_collected_block = latest_block - 5000 #for a year ago how much blocks mined?
        print('last_collected_round_id if none', last_collected_round_id)

    collect_liquidation_call_events_for_range(last_collected_block + 1, latest_block)



def get_liquidation_call_events():
    # fetch LiquidationCall events for the last 1 day
    latest_block = w3.eth.block_number

    # start block
    blocksPerDay = 7200
    days = 1
    startBlock = latest_block - blocksPerDay * days 

    logs = POOL_CONTRACT.events.LiquidationCall().get_logs(from_block=startBlock, to_block=latest_block)

    print(len(logs))
    print(logs[0])
    
    collateral_asset = logs[0]['args']['collateralAsset']
    debt_asset = logs[0]['args']['debtAsset']

    print("collateral_asset: ", collateral_asset)
    print("debt_asset: ", debt_asset)

    # event_item = {
    #     'collateral_asset': logs[0]['args']['collateralAsset'],
    #     'debt_asset': logs[0]['args']['debtAsset'],
    #     'user',
    #     'debt_to_cover',
    #     'liquidated_collateral_amount',
    #     'liquidator',
    #     'receive_a_token',
    #     'blockNumber',# event
    #     'timestamp',# block
    #     'transactionHash', # event
    #     }
    # # push item to jsonl
    # # read data and find for each its price and update jsonl
    # # 


    # data to collect: 
    columns = [
        'collateral_asset',
        'debt_asset',
        'user',
        'debt_to_cover',
        'liquidated_collateral_amount',
        'liquidator',
        'receive_a_token',
        'blockNumber',# event
        'timestamp',# block
        'transactionHash', # event
        #'collateral_decimals', # erc20 or manually from dict asset:decimals
        #'debt_decimals', # erc20 or manually from dict asset:decimals
        #'collateral_asset_price_usd', # oracle - how to find historical price?
        #'debt_asset_price_usd', # oracle
        #'previous_collateral_asset_price_usd', # to calculate how much increase
        #'previous_debt_asset_price_usd', # to calculate how much drop
        'gas_used', # receipt
        'effective_gas_price' # receipt
        ]

    

# receipt = w3.eth.get_transaction_receipt('0x98e12df11592be9a3dec4650bc5c819068350f5b6b12e987a89311df533be1ea')
# print('----')
# #print(receipt)
# print('----')
# print(receipt['gasUsed'])
# print(receipt['effectiveGasPrice'])

if __name__ == '__main__':
    # firstly try for a day -> do for a year
    # 1. pull all events for a day and push them to dictionary with asset key (they will not repeat) and extract 'keys' from dictionary -> will be a list of all assets
    get_liquidation_call_events()

    # 2. pull all historical round data for asset/usd for a day

# python -m scripts.liquidation_call_event_researcher