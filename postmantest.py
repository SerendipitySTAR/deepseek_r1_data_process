# #目前要处理的数据形式如下，如何改造data批量处理，这些数据存在另一个.jsonl文件中
# [{"role": "system", "content": "ທ່ານເປັນຜູ້ຊວຍ AI ທ່ານຈະໄດ້ຮັບ ຫນ້າ ທີ່. ທ່ານຕ້ອງສ້າງ ຄໍາ ຕອບທີ່ລະອຽດແລະຍາວ."}, {"role": "user", "content": "ກະລຸນາເພີ່ມຊ່ອງຫວ່າງລະຫວ່າງ ຄໍາ ສັບ: The roomshere ມີການອອກແບບທີ່ເປັນເອກະລັກແລະ panoramic viewofthe Ampezzo ValleyandDolomiteMountains."}, {"role": "assistant", "content": "ບັນດາຫ້ອງໃນທີ່ນີ້ມີການອອກແບບທີ່ເປັນເອກະລັກແລະມີທັດສະນະ panoramic ຂອງຮ່ອມພູ Ampezzo ແລະພູ Dolomite."}]
# [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "loop construct ကို အသုံးပြု၍ 0 မှ 9 နံပါတ်များကို print ထုတ်သည့် C++ ကုဒ်ကို ဖန်တီးပါ။"}, {"role": "assistant", "content": "#include <iostream>\n\nusing namespace std;\n\nint main() {\n    for(int i = 0; i <= 9; i++) {\n        cout << i << \" \";\n    }\n    return 0;\n} \n\n// Output: 0 1 2 3 4 5 6 7 8 9"}]
# [{"role": "system", "content": ""}, {"role": "user", "content": "အီတလီနိုင်ငံ၏ ငွေကြေးငွေကြေးသည် မည်သည့်ငွေကြေးဖြစ်သနည်း။"}, {"role": "assistant", "content": "ယူရို (€)"}]
# [{"content": "You are helpful assistant that answer in Thai.", "role": "system"}, {"content": "ผู้เขียนชาวอังกฤษที่เขียนเรื่อง 'To the Lighthouse' และ 'Mrs. Dalloway' ชื่อว่าอะไร?", "role": "user"}, {"content": "Virginia Woolf", "role": "assistant"}]


import requests
import json
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

url = "http://222.197.219.5:12025/v1/chat/completions"

headers = {
    "Accept": "application/json",
    "Content-type": "application/json"
}

# 读取 .jsonl 文件中的数据
try:
    with open("/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/testin/testin.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
        logging.debug(f"Total lines in file: {len(lines)}")
        data_list = [json.loads(line) for line in lines]
    logging.info(f"Successfully loaded {len(data_list)} items from the file.")
except Exception as e:
    logging.error(f"Failed to load data from file: {e}")
    data_list = []

for data_item in data_list:
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
        logging.debug(f"Sent request with data: {data}")
        logging.info(f"Received response with status code: {response.status_code}")

        if response.status_code == 200:
            full_content = ""  # 用于累积所有 content 内容
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith("data: "):
                        try:
                            chunk_json = json.loads(chunk_str[6:])  # 去掉 "data: " 前缀
                            logging.debug(f"Received chunk: {chunk_json}")
                            if "choices" in chunk_json and len(chunk_json["choices"]) > 0:
                                content = chunk_json["choices"][0]["delta"].get("content", "")
                                if content:
                                    full_content += content  # 将 content 拼接到完整内容中
                                    print(full_content, end="")  # 每来一个词就显示一次累积的内容
                        except json.JSONDecodeError:
                            logging.error(f"Error decoding JSON: {chunk_str}")

            # 将完整的文本内容写入文件
            with open("/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/postmantest.txt", "a", encoding="utf-8") as f:
                f.write(full_content + "\n")
            #重点检查该部分内容
            # 处理完整的文本内容转换为json格式,和该请求完整的输入拼接成一个json格式
            full_json_content =  json.dumps({"input": data_item, "output": full_content})
            # 将完整的json内容写入文件
            with open("/media/sc/KESU/博士/deepseek-R1/sea-sft-data/sea-sft-data/testout/testout.jsonl", "a", encoding="utf-8") as f:
                f.write(full_json_content + "\n")
            logging.info(f"Successfully wrote {len(full_content)} characters to the file.")
        else:
            logging.error(f"Request failed with status code {response.status_code}")
            logging.error(f"Server response: {response.text}")  # 打印服务器返回的错误消息
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
