import os
import requests
import json
import jsonlines
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm  # 引入tqdm库
import logging  # 引入logging库

# 配置日志记录
logging.basicConfig(filename='/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/testout/connect.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

url = "http://222.197.219.5:12025/v1/chat/completions"

headers = {
    "Accept": "application/json",
    "Content-type": "application/json"
}

def process_entry(entry):
    data = {
        "model": "deepseek",
        "messages": [entry],  # Send one entry at a time
        "max_tokens": 2048,
        "seed": None,
        "temperature": 1.3,
        "top_p": 0.8,
        "top_k": 50,
        "stream": True
    }

    try:
        response = requests.post(url, headers=headers, json=data, stream=True)
        if response.status_code == 200:
            full_content = ""
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith("data: "):
                        try:
                            chunk_json = json.loads(chunk_str[6:])
                            if "choices" in chunk_json and len(chunk_json["choices"]) > 0:
                                content = chunk_json["choices"][0]["delta"].get("content", "")
                                if content:
                                    full_content += content
                        except json.JSONDecodeError as e:
                            logging.error(f"JSON decode error: {e} for entry: {entry}")
                            continue
            logging.info(f"Processed entry {entry} successfully")
            return entry, full_content
        else:
            logging.error(f"Request failed with status code {response.status_code} for entry: {entry}")
            return entry, None
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred: {e} for entry: {entry}")
        return entry, None

def process_file(input_file, output_file):
    entries = []
    with jsonlines.open(input_file) as reader:
        for obj in reader:
            entries.append(obj)

    max_workers = 5  # You can adjust the number of workers as needed
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_entry = {executor.submit(process_entry, entry): entry for entry in entries}
        results = []
        for future in tqdm(as_completed(future_to_entry), total=len(entries), desc=f"Processing {input_file}"):
            entry = future_to_entry[future]
            try:
                result = future.result()
                if result[1] is not None:
                    results.append({"input": result[0], "response": result[1]})
            except Exception as e:
                logging.exception(f"Generated an exception: {e} for entry {entry}")

    with jsonlines.open(output_file, mode='w') as writer:
        writer.write_all(results)

def process_folder(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for filename in os.listdir(input_folder):
        if filename.endswith('.jsonl'):
            input_file = os.path.join(input_folder, filename)
            output_file = os.path.join(output_folder, filename)
            process_file(input_file, output_file)

# Example usage
input_folder = '/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/testin'  # 指定输入文件夹路径
output_folder = '/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/testout'  # 指定输出文件夹路径
process_folder(input_folder, output_folder)