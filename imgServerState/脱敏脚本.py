

# mask_script.py
import pandas as pd, datetime, hashlib, json
df = pd.read_excel("重庆催收案件.xlsx")
df["手机号"] = df["手机号"].str[:3] + "****" + df["手机号"].str[-4:]
df["身份证"] = df["身份证"].str[:6] + "********" + df["身份证"].str[-4:]
df.to_excel("mask_debtor.xlsx", index=False)
log = {"timestamp": datetime.datetime.now().isoformat(), "mask_hash": hashlib.sha256(df.to_json().encode()).hexdigest()[:16]}
json.dump(log, open("mask_log.json", "w"))