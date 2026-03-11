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