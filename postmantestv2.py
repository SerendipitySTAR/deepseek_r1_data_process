import json
import logging
import requests

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(filename='postmantest.log',level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

    try:
        response = requests.post(url, headers=headers, json=data, stream=True)
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
                                    print(full_content, end="")
                        except json.JSONDecodeError:
                            logger.error(f"Error decoding JSON: {chunk_str}")
            return full_content
        else:
            logger.error(f"Request failed with status code {response.status_code}")
            logger.error(f"Server response: {response.text}")  # 打印服务器返回的错误消息
            return None
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

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
    for data_item in data_list:
        full_content = send_request(url, headers, data_item)
        write_to_files(full_content, data_item, output_txt_path, output_jsonl_path)

if __name__ == "__main__":
    main()



