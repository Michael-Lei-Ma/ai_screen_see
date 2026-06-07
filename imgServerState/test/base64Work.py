import base64, requests, json
import re
# 1. 本地图片 → Base64
with open(r"D:\workdoc\123.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
image_url = f"data:image/jpeg;base64,{b64}"   # 关键格式！

# 2. 请求
url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
headers = {
    "Authorization": "Bearer sk-a417f8ac56474348a7425003d8daf9c1",
    "Content-Type": "application/json"
}
payload = {
    "model": "qwen-vl-plus",          # 或 qwen-vl-max-latest
    "messages": [
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": "请获取图片中的客户信息、"
                                     "微粒贷号码,账务信息、电话信息 、还款指引、微粒贷 的信息 组装起来只输出json字符串例如{'客户信息':{'姓名':'xxx'}},不要输出内容中的```json以及\n等字符"}
        ]}
    ]
}

resp = requests.post(url, headers=headers, json=payload)
clean = re.sub(r"```(?:json)?\n(.*?)```", r"\1", resp.json()["choices"][0]["message"]["content"], flags=re.S).strip()
data = json.loads(clean)
print(data)
print(data["客户信息"]["姓名"])
print(data["微粒贷号码"])
