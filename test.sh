curl -X POST http://222.197.219.5:12025/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "deepseek", "messages": [{"role": "system", "content": "你是一名资深政府文秘专家"}, {"role": "user", "content": "2024年度昆明理工大学分析测试基金评审结果公告"}], "max_tokens": 2046, "temperature": 1.3, "top_p": 0.8, "top_k": 50, "stream": true}'