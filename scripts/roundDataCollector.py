from web3 import Web3
from solcx import compile_source, install_solc
install_solc("0.8.13")
from dotenv import load_dotenv
load_dotenv()
import os
from datetime import datetime
from web3.exceptions import ContractLogicError
import json
from scripts.asset_to_price_feed import asset_to_feed
import time

#ASSET_ADDRESS = "0x6B175474E89094C44Da98b954EedeAC495271d0F" #DAI    
AAVE_ORACLE_ADDRESS = "0x54586bE62E3c3580375aE3723C145253060Ca0C2" #from aave docs https://aave.com/docs/resources/addresses

URL_MAINNET_ETHEREUM = os.getenv("URL_MAINNET_ETHEREUM")
w3 = Web3(Web3.HTTPProvider(URL_MAINNET_ETHEREUM))
print("Connected:", w3.is_connected())

def get_aggregator_contract(asset_address):
    # get oracle abi
    aave_oracle_compiled = compile_source('''
    pragma solidity ^0.8.0;

    /**
    * @title IAaveOracle
    * @author Aave
    * @notice Defines the basic interface for the Aave Oracle
    */
    interface IAaveOracle {
    /**
    * @dev Emitted after the base currency is set
    * @param baseCurrency The base currency of used for price quotes
    * @param baseCurrencyUnit The unit of the base currency
    */
    event BaseCurrencySet(address indexed baseCurrency, uint256 baseCurrencyUnit);

    /**
    * @dev Emitted after the price source of an asset is updated
    * @param asset The address of the asset
    * @param source The price source of the asset
    */
    event AssetSourceUpdated(address indexed asset, address indexed source);

    /**
    * @dev Emitted after the address of fallback oracle is updated
    * @param fallbackOracle The address of the fallback oracle
    */
    event FallbackOracleUpdated(address indexed fallbackOracle);

    /**
    * @notice Sets or replaces price sources of assets
    * @param assets The addresses of the assets
    * @param sources The addresses of the price sources
    */
    function setAssetSources(address[] calldata assets, address[] calldata sources) external;

    /**
    * @notice Sets the fallback oracle
    * @param fallbackOracle The address of the fallback oracle
    */
    function setFallbackOracle(address fallbackOracle) external;

    /**
    * @notice Returns a list of prices from a list of assets addresses
    * @param assets The list of assets addresses
    * @return The prices of the given assets
    */
    function getAssetsPrices(address[] calldata assets) external view returns (uint256[] memory);

    /**
    * @notice Returns the address of the source for an asset address
    * @param asset The address of the asset
    * @return The address of the source
    */
    function getSourceOfAsset(address asset) external view returns (address);

    /**
    * @notice Returns the address of the fallback oracle
    * @return The address of the fallback oracle
    */
    function getFallbackOracle() external view returns (address);
    }
                                        ''', 
                                        output_values=['abi', 'bin'])

    aave_oracle_contract_id, aave_oracle_contract_interface = aave_oracle_compiled.popitem()

    AAVE_ORACLE_ABI = aave_oracle_contract_interface['abi']
    AAVE_ORACLE_CONTRACT = w3.eth.contract(address=AAVE_ORACLE_ADDRESS, abi=AAVE_ORACLE_ABI)

    # get sourceOfAsset address and abi
    # 0x6B175474E89094C44Da98b954EedeAC495271d0F DAI
    # gives 0x5c66322CA59bB61e867B28195576DbD8dA4b08dE source address
    SOURCE_ADDRESS = AAVE_ORACLE_CONTRACT.functions.getSourceOfAsset(asset_address).call()
    print("source address ", SOURCE_ADDRESS)
    SOURCE_ABI = [{
                    "inputs": [],
                    "name": "ASSET_TO_USD_AGGREGATOR",
                    "outputs": [
                        {
                            "internalType": "contract IChainlinkAggregator",
                            "name": "",
                            "type": "address"
                        }
                    ],
                    "stateMutability": "view",
                    "type": "function"
                },
                {"inputs":[],
                 "name":"aggregator",
                 "outputs":[{"internalType":"address","name":"","type":"address"}],
                 "stateMutability":"view",
                 "type":"function"},
                 {"inputs":[],"name":"latestRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},
                 {"inputs":[{"internalType":"uint80","name":"_roundId","type":"uint80"}],"name":"getRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"}]
    SOURCE_CONTRACT = w3.eth.contract(address=SOURCE_ADDRESS, abi=SOURCE_ABI)

    # get AggregatorV3Interface address for an asset
    try:
        AGGREGATOR_ADDRESS = SOURCE_CONTRACT.functions.ASSET_TO_USD_AGGREGATOR().call()
    except:
        # AGGREGATOR_ADDRESS = SOURCE_CONTRACT.functions.aggregator().call() # do not use this aggregator, return SOURCE_CONTRACT - it is AAVE SVR Proxy for eth/usd - What about other svrs? Do they exist?
        return SOURCE_CONTRACT

    print(f"asset address: {asset_address}, aggregator address: {AGGREGATOR_ADDRESS}")
    # get aggregator abi
    aggregator_compiled = compile_source('''
                                        pragma solidity ^0.8.0;

    // solhint-disable-next-line interface-starts-with-i
    interface AggregatorV3Interface {
    function decimals() external view returns (uint8);

    function description() external view returns (string memory);

    function version() external view returns (uint256);

    function getRoundData(
        uint80 _roundId
    ) external view returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);

    function latestRoundData()
        external
        view
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
    }
                                        ''',
                                                output_values=['abi', 'bin'])

    aggregator_contract_id, aggregator_contract_interface = aggregator_compiled.popitem()
    AGGREGATOR_ABI = aggregator_contract_interface['abi']
    return w3.eth.contract(address=AGGREGATOR_ADDRESS, abi=AGGREGATOR_ABI)

def get_latest_data(asset_address):
    # get feed from asset_to_price_feed.py???
    AGGREGATOR_CONTRACT = get_aggregator_contract(asset_address)

    print("------------------ LATEST PHASE SECTION ------------------")
    # get the latest phase id -> this will be the total amount of phases for the pricefeed
    latestRoundData = AGGREGATOR_CONTRACT.functions.latestRoundData().call()

    # compute phaseId and aggregatorRoundId
    # roundId is a word containing phaseId and aggregatorRoundId
    # eg roundId = 129127208515966873796 which is                    0x00000000000000000000000000000000000000000000000700000000000030c4
    #    phaseId is roundId >> 64                                    0x>>>>>>>>>>>>>>>>00000000000000000000000000000000000000000000000700000000000030c4
    #                                                                                                                       phaseId = 7

    #   aggregatorRoundId = roundId & mask type(uint64).max          0x00000000000000000000000000000000000000000000000700000000000030c4
    #                                                             &  0x000000000000000000000000000000000000000000000000ffffffffffffffff
    #                                            aggregatorRoundId = 0x00000000000000000000000000000000000000000000000000000000000030c4
    roundId = latestRoundData[0]
    print("latest roundId: ", roundId)
    latest_phaseId = roundId >> 64
    print("latest phaseId: ", latest_phaseId) # this is the total amount of phases till now

    uint64_max = 0x000000000000000000000000000000000000000000000000ffffffffffffffff
    aggregatorRoundId = roundId & uint64_max
    print("last aggregatorRoundId: ", aggregatorRoundId)
    first_roundId_latest_phase = (latest_phaseId << 64) | 1 # 1st roundId for last phase
    print("first_roundId_latest_phase: ", first_roundId_latest_phase)
    return latest_phaseId

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
    AGGREGATOR_CONTRACT = get_aggregator_contract(asset_address)
    filename = f"aggregatorsRoundData/{AGGREGATOR_CONTRACT.address}.jsonl"    

    latest_round_data = AGGREGATOR_CONTRACT.functions.latestRoundData().call()
    print('latest_round_id ', latest_round_data[0])
    last_collected_round_id = get_last_saved_round(filename)
    print('last_collected_round_id ', last_collected_round_id)
    if last_collected_round_id is None:
        last_collected_round_id = latest_round_data[0] - 5000 #for a year for dai
        print('last_collected_round_id if none', last_collected_round_id)

    collect_round_data_for_range(asset_address, last_collected_round_id + 1, latest_round_data[0])


if __name__ == '__main__':
    asset # how many in phase 2 already for weth?

    collect_round_data(asset)
    #get_latest_data("0xdAC17F958D2ee523a2206206994597C13D831ec7")


#python -m scripts.roundDataCollector