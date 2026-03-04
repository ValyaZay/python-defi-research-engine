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
        'gas_used', # receipt
        'effective_gas_price' # receipt
        ]

    collateral_asset = logs[0]['args']['collateralAsset']
    debt_asset = logs[0]['args']['debtAsset']

    print("collateral_asset: ", collateral_asset)
    print("debt_asset: ", debt_asset)

# receipt = w3.eth.get_transaction_receipt('0x98e12df11592be9a3dec4650bc5c819068350f5b6b12e987a89311df533be1ea')
# print('----')
# #print(receipt)
# print('----')
# print(receipt['gasUsed'])
# print(receipt['effectiveGasPrice'])

if __name__ == '__main__':
    get_liquidation_call_events()