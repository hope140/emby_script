import os
import shutil
import logging
import json

def set_log_level(config):
    log_level_config = config.get('log_level', 'INFO')
    log_level = getattr(logging, log_level_config.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

def copy_files(src_folder, dst_folder, exclude_exts=('.mkv', '.mp4', '.ts'), max_size_mb=100, on_duplicate='overwrite'):
    """
    复制文件从 src_folder 到 dst_folder。

    Args:
        src_folder (str): 源文件夹路径。
        dst_folder (str): 目标文件夹路径。
        exclude_exts (tuple): 要排除的文件扩展名列表，默认排除 ('.mkv', '.mp4')。
        max_size_mb (int): 文件的最大大小（以 MB 为单位），默认为 100。
        on_duplicate (str): 当目标文件夹中存在同名文件时的行为，可选值 'skip' 或 'overwrite'，默认为 'overwrite'。
    """
    logging.info(f"Starting operation: Copying files from {src_folder} to {dst_folder}")

    # 确保目标文件夹存在
    if not os.path.exists(dst_folder):
        os.makedirs(dst_folder)
        logging.info(f"Destination folder created: {dst_folder}")
    else:
        logging.info(f"Destination folder already exists: {dst_folder}")

    # 递归遍历源文件夹中的所有文件和子文件夹
    for root, dirs, files in os.walk(src_folder):
        for filename in files:
            file_path = os.path.join(root, filename)
            logging.debug(f"Processing file: {file_path}")

            # 检查文件扩展名
            if any(filename.endswith(ext) for ext in exclude_exts):
                logging.info(f"Skipped file due to excluded extension: {file_path}")
                continue

            # 获取文件大小
            file_size = os.path.getsize(file_path)

            # 检查文件大小是否超出限制
            if file_size > max_size_mb * 1024 * 1024:
                logging.info(f"Skipped file due to excessive size: {file_path} ({file_size / 1024 / 1024:.2f} MB)")
                continue

            # 计算目标路径
            relative_path = os.path.relpath(root, src_folder)
            dst_path = os.path.join(dst_folder, relative_path)
            dst_file_path = os.path.join(dst_path, filename)

            # 确保目标路径存在
            os.makedirs(dst_path, exist_ok=True)

            # 检查文件是否已存在
            if os.path.exists(dst_file_path):
                if on_duplicate == 'skip':
                    logging.info(f"Skipped existing file: {dst_file_path}")
                    continue
                elif on_duplicate == 'overwrite':
                    logging.info(f"Overwriting existing file: {dst_file_path}")
                    os.remove(dst_file_path)
                else:
                    raise ValueError("Invalid value for 'on_duplicate'. Use 'skip' or 'overwrite'.")

            # 复制文件
            shutil.copy2(file_path, dst_file_path)
            logging.info(f"Copied file: {file_path} to {dst_file_path}")

if __name__ == "__main__":
    # 读取配置文件
    with open('config.json', 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)

    # 设置日志配置级别
    set_log_level(config)

    folder_pairs = config['folder_pairs']
    exclude_exts = tuple(config['exclude_exts'])
    max_size_mb = config['max_size_mb']
    on_duplicate = config['on_duplicate']

    # 使用读取到的参数调用 copy_files 函数
    for pair in folder_pairs:
        src_folder = pair['src_folder']
        dst_folder = pair['dst_folder']
        copy_files(src_folder, dst_folder, exclude_exts, max_size_mb, on_duplicate)

    logging.info("所有操作完成，按任意键关闭...")
    input("所有操作完成，按任意键关闭...")
