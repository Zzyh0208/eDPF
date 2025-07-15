import pandas as pd
import numpy as np


def modify_matrix(input_file, new_size):
    # 读取csv文件
    df = pd.read_csv(input_file, header=None)

    # 提取数据矩阵并排除第一行
    data = df.iloc[1:].values
    n = len(data)

    # 如果输入的new_size大于n，进行填充
    if new_size > n:
        # 创建一个新的矩阵，初始化为0
        new_matrix = np.zeros((new_size, new_size))
        # 将原始矩阵复制到新矩阵的左上角
        new_matrix[:n, :n] = data
        # 处理第一行的裁剪或填充
        first_row = np.concatenate((df.iloc[0, :n].values, np.zeros(new_size - n)))
    # 如果输入的new_size小于n，进行裁剪
    elif new_size < n:
        # 裁剪矩阵
        new_matrix = data[:new_size, :new_size]
        # 裁剪第一行
        first_row = df.iloc[0, :new_size].values
    else:
        # new_size等于n，不变
        new_matrix = data
        first_row = df.iloc[0, :n].values

    # 拼接第一行
    result = np.vstack((first_row, new_matrix))

    return result


# 示例调用
input_file = 'data_input/Lorenz96_var20_force10_t250_struct_0.csv'  # 请根据实际文件路径修改
new_size = 12  # 例如选择填充或裁剪到25
result = modify_matrix(input_file, new_size)

# 将结果保存为CSV文件
output_file = 'data_input/Lorenz96_var20_force10_t250_struct_0.csv'
pd.DataFrame(result).to_csv(output_file, header=False, index=False)

print(f"矩阵已保存为 {output_file}")
