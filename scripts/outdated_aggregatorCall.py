from web3 import Web3
from solcx import compile_source, install_solc
install_solc("0.8.13")
from dotenv import load_dotenv
load_dotenv()
import os
from web3.exceptions import ContractLogicError
import json
import jmespath
import sys



class RoundData:
    def __init__(self, roundId, answer, startedAt, updatedAt):
        self.roundId = roundId
        self.answer = answer
        self.startedAt = startedAt
        self.updatedAt = updatedAt

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
AAVE_ORACLE_ADDRESS = "0x54586bE62E3c3580375aE3723C145253060Ca0C2"
AAVE_ORACLE_CONTRACT = w3.eth.contract(address=AAVE_ORACLE_ADDRESS, abi=AAVE_ORACLE_ABI)

# get sourceOfAsset address and abi
# 0x6B175474E89094C44Da98b954EedeAC495271d0F DAI
# gives 0x5c66322CA59bB61e867B28195576DbD8dA4b08dE source address
SOURCE_ADDRESS = AAVE_ORACLE_CONTRACT.functions.getSourceOfAsset("0x6B175474E89094C44Da98b954EedeAC495271d0F").call() #returns address of source of asset
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
# aggregator_compiled = compile_source('''
# pragma solidity ^0.8.0;

# interface AggregatorInterface {
#   function latestAnswer() external view returns (int256);

#   function latestTimestamp() external view returns (uint256);

#   function latestRound() external view returns (uint256);

#   function getAnswer(uint256 roundId) external view returns (int256);

#   function getTimestamp(uint256 roundId) external view returns (uint256);

#   event AnswerUpdated(int256 indexed current, uint256 indexed roundId, uint256 updatedAt);

#   event NewRound(uint256 indexed roundId, address indexed startedBy, uint256 startedAt);
# }
#                                                ''',
#                                                output_values=['abi', 'bin'])

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
aggregator_contract = w3.eth.contract(address=AGGREGATOR_ADDRESS, abi=AGGREGATOR_ABI)

# get latestRoundData

latestRoundData = aggregator_contract.functions.latestRoundData().call()

# put all this into a class
print(f'roundId: {latestRoundData[0]}')
print(f'answer: {latestRoundData[1]}')
print(f'startedAt: {latestRoundData[2]}')
print(f'updatedAt: {latestRoundData[3]}')

# compute phaseId and aggregatorRoundId
# roundId is a word containing phaseId and aggregatorRoundId
# eg roundId = 129127208515966873796 which is                    0x00000000000000000000000000000000000000000000000700000000000030c4
#    phaseId is roundId >> 64                                    0x>>>>>>>>>>>>>>>>00000000000000000000000000000000000000000000000700000000000030c4
#                                                                                                                       phaseId = 7

#   aggregatorRoundId = roundId & mask type(uint64).max          0x00000000000000000000000000000000000000000000000700000000000030c4
#                                                             &  0x000000000000000000000000000000000000000000000000ffffffffffffffff
#                                            aggregatorRoundId = 0x00000000000000000000000000000000000000000000000000000000000030c4
roundId = latestRoundData[0]
phaseId = roundId >> 64
print(phaseId)

uint64_max = 0x000000000000000000000000000000000000000000000000ffffffffffffffff
aggregatorRoundId = roundId & uint64_max
print(aggregatorRoundId)

roundId_test_1 = (7 << 64) | 1 # 1st roundId for phase 7
roundId_test_2 = roundId - aggregatorRoundId + 1
print(roundId_test_1)
print(roundId_test_2)
print(roundId_test_1 == roundId_test_2)

# 129127208515966873792 updatedAt 1771928471 
# 129127208515966873795 updatedAt 1771939367
# 129127208515966873795 end phase 7 roundId
#.129127208515966861313......................start phase 7 roundId
# 110680464442257309697 start phase 6
# 110680464442257322604 end phase 6
# 12908

# phaseId_6 = 110680464442257322604 >> 64
# print("phase 6: ", phaseId_6)

# uint64_max = 0x000000000000000000000000000000000000000000000000ffffffffffffffff
# aggregatorRoundId_6 = 110680464442257322604 & uint64_max
# print("aggregatorroundId 6: ", aggregatorRoundId_6)

# roundId_test_1 = 129127208515966861313 # phase 7 start

# open file and get an item
#targetTimestamp = 1726743440
def something(priceFeed, timestamp):
    targetTimestamp = int(timestamp)
    query_updated_at = f"[?updatedAt < `{targetTimestamp}`]" # note backticks to pass a number into a query

    #with open("aggregatorsRoundData/0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9.json") as f:
    with open(f"aggregatorsRoundData/{priceFeed}.json") as f:
        jsonRoundData = json.load(f)
    # df = pd.DataFrame(jsonRoundData)
    # roundDataSearched = df.loc[(df['updatedAt'] > 1726783343) & (df['updatedAt'] < 1726790687), "answer"]
    # if not roundDataSearched.empty:
    #     answer = roundDataSearched.iloc[0]
    result = jmespath.search(query_updated_at, jsonRoundData)
    print(result[-1])
    answer = result[-1]['answer']
    print(answer)
    return answer
# if the latest roundId in json array != roundId from latestRoundData -> add roundDataItems for that range (roundIdFromJson, latestRoundId) - move this to a separate function later
# roundData = []
# for i in range(roundId_test_1, roundId_test_1 + 50):
#     try:
#         data = aggregator_contract.functions.getRoundData(roundId_test_1).call()
#         #roundDataItem = RoundData(data[0], data[1], data[2], data[3])
#         roundDataItem = {
#             "roundId": data[0],
#             "answer": data[1],
#             "startedAt": data[2],
#             "updatedAt": data[3]
#         }
        
#         print(f"Round {roundId_test_1}: {data}") 
#         if(data[1] == 0):
#           break

#         roundData.append(roundDataItem)
#         roundId_test_1 += 1

#     except ContractLogicError:
#         print(f"Reverted at round {roundId_test_1}. Stopping.")
#         break
    
# # save array of objects to the file: aggregatorAddress.py -> data[RoundData]
# with open("aggregatorsRoundData/0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9.json", "a") as f:
#     json.dump(roundData, f)

#####################################
# Define a class to represent objects
# class Item:
#     def __init__(self, name, price):
#         self.name = name
#         self.price = price

# # Create a list of objects
# items = [
#     Item("Laptop", 1000),
#     Item("Phone", 700),
#     Item("Tablet", 400)
# ]

# # Check if any object has a name 'Phone'
# value_to_check = "Phone"
# exists = any(item.name == value_to_check for item in items)

# print("Value exists:", exists)
def main():
    print("Hello")
    
if __name__ == "__main__":
    # retrieve arguments passed from the liquidationCall
    try:        
        receivedPriceFeedAddr = sys.argv[1]
        receivedTimestamp = sys.argv[2]
        
        answer_to_return = something()
        print(answer_to_return)
    except IndexError:
        print("Error: missing arguments")

