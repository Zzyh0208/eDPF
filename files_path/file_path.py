# 所需文件地址存储
import os

# 获得该文件的上级目录
standard = os.path.abspath('..')

# 获取emulation文件地址
emulation_path = os.path.join(standard, "emulation\\")

# 获取data的地址
data_path = os.path.join(standard, "data\\")

# 获取screen文件地址
screen_path = os.path.join(standard, "screen\\")
