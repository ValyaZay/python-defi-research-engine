import json

def convert(path_jsonl, path_json):
    data = []

    with open(path_jsonl, 'r') as jsonl_file:
        for line in jsonl_file:
            data.append(json.loads(line.strip()))

    with open(path_json, 'w') as json_file:
        json.dump(data, json_file, indent=4)

if __name__ == '__main__':
    convert('aggregatorsRoundData/testData.jsonl', 'aggregatorsRoundData/testDataConverted.json')