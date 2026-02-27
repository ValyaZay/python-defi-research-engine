from web3 import Web3
from solcx import compile_source, install_solc
install_solc("0.8.13")
from dotenv import load_dotenv
load_dotenv()
import os
from datetime import datetime
from web3.exceptions import ContractLogicError
import json

ASSET_ADDRESS = "0x6B175474E89094C44Da98b954EedeAC495271d0F" #DAI
URL_MAINNET_ETHEREUM = os.getenv("URL_MAINNET_ETHEREUM")
w3 = Web3(Web3.HTTPProvider(URL_MAINNET_ETHEREUM))
print("Connected:", w3.is_connected())

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
AAVE_ORACLE_ADDRESS = "0x54586bE62E3c3580375aE3723C145253060Ca0C2" #from aave docs https://aave.com/docs/resources/addresses
AAVE_ORACLE_CONTRACT = w3.eth.contract(address=AAVE_ORACLE_ADDRESS, abi=AAVE_ORACLE_ABI)

# get sourceOfAsset address and abi
# 0x6B175474E89094C44Da98b954EedeAC495271d0F DAI
# gives 0x5c66322CA59bB61e867B28195576DbD8dA4b08dE source address
SOURCE_ADDRESS = AAVE_ORACLE_CONTRACT.functions.getSourceOfAsset(ASSET_ADDRESS).call()
print(f"source address: {SOURCE_ADDRESS}")
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
              }]

SOURCE_CONTRACT = w3.eth.contract(address=SOURCE_ADDRESS, abi=SOURCE_ABI)


# get AggregatorV3Interface address for an asset
# 0x6B175474E89094C44Da98b954EedeAC495271d0F DAI
# 0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9 dai/usd price feed
AGGREGATOR_ADDRESS = SOURCE_CONTRACT.functions.ASSET_TO_USD_AGGREGATOR().call()
print(f"aggregator address: {AGGREGATOR_ADDRESS}")

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
AGGREGATOR_CONTRACT = w3.eth.contract(address=AGGREGATOR_ADDRESS, abi=AGGREGATOR_ABI)


def get_latest_data():
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

def validate_round_id():
    round_id = 129127208515966873862
    uint64_max = 0x000000000000000000000000000000000000000000000000ffffffffffffffff
    aggregatorRoundId = round_id & uint64_max
    phaseId = round_id >> 64
    print(f"phaseId: {phaseId}, roundsInPhase: ", aggregatorRoundId)

def get_start_data_from_phases(latest_phaseId):
    print("------------------ GET START DATA SECTION ------------------")
    # get first roundId in the phase and start timestamp
    for phaseId in range(1, latest_phaseId + 1):
        first_roundId_in_phase = (phaseId << 64) | 1

        try:
            first_roundData_in_phase = AGGREGATOR_CONTRACT.functions.getRoundData(first_roundId_in_phase).call()
        except ContractLogicError:
            print(f"Reverted at round {first_roundId_in_phase}. No data.")
            continue

        phase_started_at_timestamp = first_roundData_in_phase[2]
        phase_started_on_date = datetime.fromtimestamp(phase_started_at_timestamp).date()
        print(f"loop data: phaseId {phaseId}, first_roundId_in_phase {first_roundId_in_phase}, phase_started_on_date {phase_started_on_date}")

# get last roundId in the phase, end timestamp and amount of rounds in the phase
def get_end_data_from_phases():    
    loop_from_round_id = 110680464442257322597
    while True:
        try:
            data = AGGREGATOR_CONTRACT.functions.getRoundData(loop_from_round_id).call()
            
            print(f"Round {loop_from_round_id}: {data}") 
            if(data[1] == 0):
                break

            loop_from_round_id += 1 #start from 1000 items step

        except ContractLogicError:
            print(f"Reverted at round {loop_from_round_id}. Stopping.")
            break

def collect_round_data_for_last_year(price_feed_address):
    # 129127208515966868862 dai/usd round id for the year ago ~ 5000 entries for dai/usd
    # ...................  ....... round id for the year ago
    round_id_year_ago = 129127208515966868862 #dai/usd round id for the year ago ~ 5000 entries for dai/usd
    #                   129127208515966869861
    #                   129127208515966870861
    #                   129127208515966871861
    roundData = []
    for round_id in range(round_id_year_ago + 4000, 129127208515966873866): #chunks for getting historical data
        try:
            data = AGGREGATOR_CONTRACT.functions.getRoundData(round_id).call()
            roundDataItem = {
                "roundId": data[0],
                "answer": data[1],
                "startedAt": data[2],
                "updatedAt": data[3]
            }
            
            print(f"Round {round_id}: {data}") 
            if(data[1] == 0):
                break

            roundData.append(roundDataItem)
            round_id += 1

        except ContractLogicError:
            print(f"Reverted at round {round_id}. Stopping.")
            break    

        # save array of objects to the file: <price_feed_address>.json
        with open(f"aggregatorsRoundData/{price_feed_address}.json", "a") as f:
            json.dump(roundData, f)

def get_date_from_round_id():
    end_round_id = 110680464442257322604
    try:
        end_round_data_in_phase = AGGREGATOR_CONTRACT.functions.getRoundData(end_round_id).call()
    except ContractLogicError:
        print(f"Reverted at round {end_round_id}. No data.")
        
    phase_ended_at_timestamp = end_round_data_in_phase[2]
    phase_ended_on_date = datetime.fromtimestamp(phase_ended_at_timestamp).date()
    print("phase_ended_on_date: ", phase_ended_on_date)






if __name__ == '__main__':
    #latest_phase_id = get_latest_data()
    #get_start_data_from_phases(latest_phaseId=7)
    
    #get_end_data_from_phases()

    #get_date_from_round_id()
    
    #validate_round_id()

    collect_round_data_for_last_year("0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9")