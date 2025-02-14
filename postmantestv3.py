import json
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm
import time

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(filename='postmantest.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_jsonl_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            logger.debug(f"Total lines in file: {len(lines)}")
            data_list = [json.loads(line) for line in lines]
        logger.info(f"Successfully loaded {len(data_list)} items from the file.")
        return data_list
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def send_request(url, headers, data_item):
    data = {
        "model": "deepseek",
        "messages": data_item,
        "max_tokens": 2046,
        "seed": None,  # 设置一个固定的 seed 值
        "temperature": 1.3,
        "top_p": 0.8,
        "top_k": 50,
        "stream": True
    }

    start_time = time.time()  # 记录请求开始时间
    try:
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=10)  # 添加 timeout 参数
        logger.debug(f"Sent request with data: {data}")
        logger.info(f"Received response with status code: {response.status_code}")

        if response.status_code == 200:
            full_content = ""
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith("data: "):
                        chunk_str = chunk_str[6:]  # 去掉 "data: " 前缀
                        if chunk_str.strip() == "[DONE]":
                            logger.info("Received [DONE] signal, ending stream.")
                            break
                        try:
                            chunk_json = json.loads(chunk_str)
                            logger.debug(f"Received chunk: {chunk_json}")
                            if "choices" in chunk_json and len(chunk_json["choices"]) > 0:
                                content = chunk_json["choices"][0]["delta"].get("content", "")
                                if content:
                                    full_content += content  # 将 content 拼接到完整内容中
                        except json.JSONDecodeError:
                            logger.error(f"Error decoding JSON: {chunk_str}")
            end_time = time.time()  # 记录请求结束时间
            logger.info(f"Request took {end_time - start_time:.2f} seconds")
            return full_content
        else:
            logger.error(f"Request failed with status code {response.status_code}")
            logger.error(f"Server response: {response.text}")  # 打印服务器返回的错误消息
            raise requests.RequestException(f"Request failed with status code {response.status_code}")
    except requests.RequestException as e:
        end_time = time.time()  # 记录请求结束时间
        logger.error(f"Request took {end_time - start_time:.2f} seconds")
        logger.error(f"Request failed: {e}")
        raise

def write_to_files(full_content, data_item, output_txt_path, output_jsonl_path):
    if full_content:
        with open(output_txt_path, "a", encoding="utf-8") as f:
            f.write(full_content + "\n")
        full_json_content = json.dumps({"input": data_item, "output": full_content}, ensure_ascii=False)
        with open(output_jsonl_path, "a", encoding="utf-8") as f:
            f.write(full_json_content + "\n")
        logger.info(f"Successfully wrote {len(full_content)} characters to the file.")

def main():
    url = "http://222.197.219.5:12025/v1/chat/completions"
    headers = {
        "Accept": "application/json",
        "Content-type": "application/json"
    }
    input_file_path = "/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/testin/testin.jsonl"
    output_txt_path = "/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/postmantest.txt"
    output_jsonl_path = "/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/testout/testout.jsonl"

    data_list = read_jsonl_file(input_file_path)
    with ThreadPoolExecutor(max_workers=2) as executor:  # 使用 ThreadPoolExecutor 进行并发处理
        future_to_data_item = {executor.submit(send_request, url, headers, data_item): data_item for data_item in data_list}
        for future in tqdm(as_completed(future_to_data_item), total=len(future_to_data_item), desc="Processing requests"):
            data_item = future_to_data_item[future]
            try:
                full_content = future.result()
                write_to_files(full_content, data_item, output_txt_path, output_jsonl_path)
            except Exception as e:
                logger.error(f"Error processing {data_item}: {e}")

if __name__ == "__main__":
    main()