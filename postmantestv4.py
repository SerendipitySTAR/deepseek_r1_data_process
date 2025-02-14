import json
import logging
import asyncio
import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor

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
async def send_request(session, url, headers, data_item):
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
        async with session.post(url, headers=headers, json=data) as response:
            logger.debug(f"Sent request with data: {data}")
            logger.info(f"Received response with status code: {response.status}")

            if response.status == 200:
                full_content = ""
                async for line in response.content:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        line = line[6:]  # 去掉 "data: " 前缀
                        if line.strip() == "[DONE]":
                            logger.info("Received [DONE] signal, ending stream.")
                            break
                        try:
                            line_json = json.loads(line)
                            logger.debug(f"Received chunk: {line_json}")
                            if "choices" in line_json and len(line_json["choices"]) > 0:
                                content = line_json["choices"][0]["delta"].get("content", "")
                                if content:
                                    full_content += content  # 将 content 拼接到完整内容中
                        except json.JSONDecodeError:
                            logger.error(f"Error decoding JSON: {line}")
                end_time = time.time()  # 记录请求结束时间
                logger.info(f"Request took {end_time - start_time:.2f} seconds")
                return full_content
            else:
                logger.error(f"Request failed with status code {response.status}")
                logger.error(f"Server response: {await response.text()}")  # 打印服务器返回的错误消息
                raise aiohttp.ClientError(f"Request failed with status code {response.status}")
    except aiohttp.ClientError as e:
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

async def main():
    url = "http://222.197.219.5:12025/v1/chat/completions"
    headers = {
        "Accept": "application/json",
        "Content-type": "application/json"
    }
    input_file_path = "/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/testin/testin.jsonl"
    output_txt_path = "/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/postmantest.txt"
    output_jsonl_path = "/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/testout/testout.jsonl"

    data_list = read_jsonl_file(input_file_path)
    async with aiohttp.ClientSession() as session:
        with ThreadPoolExecutor(max_workers=10) as executor:  # 使用 ThreadPoolExecutor
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, lambda d: asyncio.run(send_request(session, url, headers, d)), data_item)
                for data_item in data_list
            ]
            for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing requests"):
                try:
                    full_content = await future
                    data_item = data_list[tasks.index(future)]
                    write_to_files(full_content, data_item, output_txt_path, output_jsonl_path)
                except Exception as e:
                    data_item = data_list[tasks.index(future)]
                    logger.error(f"Error processing {data_item}: {e}")

if __name__ == "__main__":
    asyncio.run(main())