from datetime import datetime, timedelta


def is_valid_id(id_number):
    """验证身份证号是否合法（校验格式和校验码）"""
    if len(id_number) != 18:
        return False
    if not id_number[:17].isdigit():
        return False
    # 加权因子
    factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    # 校验码对应表
    check_codes = '10X98765432'

    total = sum(int(id_number[i]) * factors[i] for i in range(17))
    check_code = check_codes[total % 11]
    return id_number[17] == check_code


start_date = datetime(1978, 11, 1)
end_date = datetime(1979, 10, 31)
current_date = start_date

valid_ids = []

while current_date <= end_date:
    date_str = current_date.strftime("%Y%m%d")
    id_number = "441827" + date_str + "8918"  # 350521为地址码，401为顺序码（男性）
    if is_valid_id(id_number):
        valid_ids.append(id_number)
    current_date += timedelta(days=1)

print(f"共找到{len(valid_ids)}个合法身份证号：")
for id_num in valid_ids:
    print(id_num)
