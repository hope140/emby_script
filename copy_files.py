import os
import shutil
import logging
import json
import hashlib

def set_log_level(config):
    """
    设置日志级别。

    Args:
        config (dict): 配置文件内容。
    """
    log_level_config = config.get('log_level', 'INFO')
    log_level = getattr(logging, log_level_config.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

def compute_file_hash(file_path):
    """
    计算文件的哈希值。

    Args:
        file_path (str): 文件路径。

    Returns:
        str: 文件的 MD5 哈希值。
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def copy_files(src_folder, dst_folder, exclude_exts=('.mkv', '.mp4', '.ts'), max_size_mb=100, on_duplicate='overwrite'):
    """
    复制文件从 src_folder 到 dst_folder，并删除目标文件夹中不同于源文件夹的文件（.strm 文件除外）。

    Args:
        src_folder (str): 源文件夹路径。
        dst_folder (str): 目标文件夹路径。
        exclude_exts (tuple): 要排除的文件扩展名列表，默认排除 ('.mkv', '.mp4')。
        max_size_mb (int): 文件的最大大小（以 MB 为单位），默认为 100。
        on_duplicate (str): 当目标文件夹中存在同名文件时的行为，可选值 'skip' 或 'overwrite'，默认为 'overwrite'。
    """
    logging.info(f"开始操作：从 {src_folder} 复制文件到 {dst_folder}")

    # 确保目标文件夹存在
    if not os.path.exists(dst_folder):
        os.makedirs(dst_folder)
        logging.info(f"目标文件夹已创建: {dst_folder}")
    else:
        logging.info(f"目标文件夹已存在: {dst_folder}")

    # 初始化统计变量
    total_files = 0
    skipped_files = 0
    copied_files = 0
    overwritten_files = 0
    deleted_files = 0

    # 递归遍历源文件夹中的所有文件和子文件夹
    src_files = set()
    for root, dirs, files in os.walk(src_folder):
        for filename in files:
            file_path = os.path.join(root, filename)
            logging.debug(f"处理文件: {file_path}")
            relative_path = os.path.relpath(file_path, src_folder)
            src_files.add(relative_path)
            total_files += 1

            # 检查文件扩展名
            if any(filename.endswith(ext) for ext in exclude_exts):
                logging.info(f"跳过文件，因为扩展名被排除: {file_path}")
                skipped_files += 1
                continue

            # 获取文件大小
            file_size = os.path.getsize(file_path)

            # 检查文件大小是否超出限制
            if file_size > max_size_mb * 1024 * 1024:
                logging.info(f"跳过文件，因为文件大小超出限制: {file_path} ({file_size / 1024 / 1024:.2f} MB)")
                skipped_files += 1
                continue

            # 计算目标路径
            dst_path = os.path.join(dst_folder, os.path.dirname(relative_path))
            dst_file_path = os.path.join(dst_path, os.path.basename(relative_path))

            # 确保目标路径存在
            os.makedirs(dst_path, exist_ok=True)

            # 检查文件是否已存在
            if os.path.exists(dst_file_path):
                if on_duplicate == 'skip':
                    # 计算源文件和目标文件的哈希值
                    src_hash = compute_file_hash(file_path)
                    dst_hash = compute_file_hash(dst_file_path)
                    if src_hash == dst_hash:
                        logging.info(f"跳过文件，因为文件已经存在且内容相同: {dst_file_path}")
                        skipped_files += 1
                        continue
                    else:
                        logging.info(f"覆盖文件，因为现有文件内容不同: {dst_file_path}")
                        overwritten_files += 1
                elif on_duplicate == 'overwrite':
                    logging.info(f"覆盖已存在的文件: {dst_file_path}")
                    os.remove(dst_file_path)
                    overwritten_files += 1
                else:
                    raise ValueError("无效的 'on_duplicate' 值。请使用 'skip' 或 'overwrite'。")

            # 复制文件
            shutil.copy2(file_path, dst_file_path)
            logging.info(f"复制文件: {file_path} 到 {dst_file_path}")
            copied_files += 1

    # 删除目标文件夹中异于源文件夹的文件（.strm 文件除外）
    for root, dirs, files in os.walk(dst_folder, topdown=False):
        for filename in files:
            if filename.endswith('.strm'):
                continue
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, dst_folder)
            if relative_path not in src_files:
                logging.info(f"删除文件: {file_path}")
                os.remove(file_path)
                deleted_files += 1

        # 删除空目录
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if not os.listdir(dir_path):
                logging.info(f"删除空目录: {dir_path}")
                os.rmdir(dir_path)

    # 输出总计统计信息
    logging.info(f"总计处理的文件数: {total_files}")
    logging.info(f"总计跳过的文件数: {skipped_files}")
    logging.info(f"总计复制的文件数: {copied_files}")
    logging.info(f"总计覆盖的文件数: {overwritten_files}")
    logging.info(f"总计删除的文件数: {deleted_files}")

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
