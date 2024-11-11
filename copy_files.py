import os
import shutil
import logging
import json
import hashlib
import time
import threading

# 用于存储处理过的子文件夹记录的文件路径
PROCESSED_SUBFOLDERS_FILE = 'processed_subfolders.json'

def set_log_level(config):
    """
    设置日志级别。
    """
    log_level_config = config.get('log_level', 'INFO')
    log_level = getattr(logging, log_level_config.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

def compute_file_hash(file_path, timeout=10):
    """
    计算文件的哈希值，并在超时后返回 None。
    """
    def compute_hash():
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    hash_result = [None]
    def worker():
        hash_result[0] = compute_hash()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        logging.warning(f"文件读取超时，跳过: {file_path}")
        return None
    return hash_result[0]

def load_processed_subfolders():
    """
    加载已处理过的子文件夹记录。
    """
    if os.path.exists(PROCESSED_SUBFOLDERS_FILE):
        with open(PROCESSED_SUBFOLDERS_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_processed_subfolders(processed_subfolders):
    """
    保存已处理过的子文件夹记录。
    """
    with open(PROCESSED_SUBFOLDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(processed_subfolders), f)

def create_strm_file(src_folder, dst_folder, webdav_base_url, exclude_prefix, config, video_exts=('.mkv', '.iso', '.ts', '.mp4', '.avi', '.rmvb', '.wmv', '.m2ts', '.mpg', '.flv', '.rm', '.mov')):
    """
    根据源文件夹中的视频文件生成 .strm 文件。
    """
    logging.info(f"开始生成 .strm 文件：从 {src_folder} 到 {dst_folder}")

    # 确保目标文件夹存在
    if not os.path.exists(dst_folder):
        os.makedirs(dst_folder)
        logging.info(f"目标文件夹已创建: {dst_folder}")
    else:
        logging.info(f"目标文件夹已存在: {dst_folder}")

    # 初始化统计变量
    total_files = 0
    generated_strm_files = 0

    # 加载已处理过的子文件夹记录
    processed_subfolders = load_processed_subfolders()
    force_process_subfolders = set(config.get('force_process_subfolders', []))

    # 递归遍历源文件夹中的所有文件和子文件夹
    for root, dirs, files in os.walk(src_folder):
        # 检查当前子文件夹是否已经处理过
        relative_subfolder = os.path.relpath(root, src_folder)
        if relative_subfolder in processed_subfolders and not any(relative_subfolder.startswith(fp) for fp in force_process_subfolders):
            logging.info(f"跳过已处理过的子文件夹: {relative_subfolder}")
            continue

        for filename in files:
            file_path = os.path.join(root, filename)
            logging.debug(f"处理文件: {file_path}")
            relative_path = os.path.relpath(file_path, src_folder)
            total_files += 1

            # 检查文件扩展名
            if any(filename.endswith(ext) for ext in video_exts):
                # 计算目标路径
                dst_path = os.path.join(dst_folder, os.path.dirname(relative_path))
                dst_file_path = os.path.join(dst_path, os.path.splitext(filename)[0] + '.strm')

                # 确保目标路径存在
                os.makedirs(dst_path, exist_ok=True)

                # 生成 .strm 文件内容
                # 计算排除前缀后的路径
                absolute_path = os.path.abspath(os.path.join(dst_folder, relative_path))
                relative_webdav_path = os.path.relpath(absolute_path, exclude_prefix).replace(os.sep, '/')
                webdav_url = f"{webdav_base_url}/{relative_webdav_path}"

                # 检查 .strm 文件是否已存在且内容相同
                if os.path.exists(dst_file_path):
                    try:
                        with open(dst_file_path, 'r', encoding='utf-8') as existing_strm_file:
                            existing_content = existing_strm_file.read().strip()
                    except Exception as e:
                        logging.error(f"读取 .strm 文件时出错: {dst_file_path} - {e}")
                        continue
                    if existing_content == webdav_url:
                        logging.info(f"跳过 .strm 文件，因为内容相同: {dst_file_path}")
                        continue

                try:
                    with open(dst_file_path, 'w', encoding='utf-8') as strm_file:
                        strm_file.write(webdav_url)
                except Exception as e:
                    logging.error(f"写入 .strm 文件时出错: {dst_file_path} - {e}")
                    continue

                logging.info(f"生成 .strm 文件: {dst_file_path} 内容: {webdav_url}")
                generated_strm_files += 1

    # 返回总计统计信息
    return total_files, generated_strm_files

def copy_files(src_folder, dst_folder, exclude_exts, max_size_mb, on_duplicate, timeout, config):
    """
    复制文件从 src_folder 到 dst_folder，并删除目标文件夹中不同于源文件夹的文件（.strm 文件除外）。
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
    timeout_files = []

    # 加载已处理过的子文件夹记录
    processed_subfolders = load_processed_subfolders()
    force_process_subfolders = set(config.get('force_process_subfolders', []))

    # 递归遍历源文件夹中的所有文件和子文件夹
    src_files = set()
    for root, dirs, files in os.walk(src_folder):
        # 检查当前子文件夹是否已经处理过
        relative_subfolder = os.path.relpath(root, src_folder)
        if relative_subfolder in processed_subfolders and not any(relative_subfolder.startswith(fp) for fp in force_process_subfolders):
            logging.info(f"跳过已处理过的子文件夹: {relative_subfolder}")
            continue

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
                    src_hash = compute_file_hash(file_path, timeout)
                    dst_hash = compute_file_hash(dst_file_path, timeout)
                    if src_hash is None or dst_hash is None:
                        timeout_files.append(file_path)
                        continue
                    if src_hash == dst_hash:
                        logging.info(f"跳过文件，因为文件已经存在且内容相同: {dst_file_path}")
                        skipped_files += 1
                        continue
                    else:
                        logging.info(f"覆盖文件，因为现有文件内容不同: {dst_file_path}")
                        try:
                            os.remove(dst_file_path)
                        except Exception as e:
                            logging.error(f"删除目标文件时出错: {dst_file_path} - {e}")
                            continue
                        overwritten_files += 1
                elif on_duplicate == 'overwrite':
                    logging.info(f"覆盖已存在的文件: {dst_file_path}")
                    try:
                        os.remove(dst_file_path)
                    except Exception as e:
                        logging.error(f"删除目标文件时出错: {dst_file_path} - {e}")
                        continue
                    overwritten_files += 1
                else:
                    raise ValueError("无效的 'on_duplicate' 值。请使用 'skip' 或 'overwrite'。")

            # 复制文件
            start_time = time.time()
            try:
                shutil.copy2(file_path, dst_file_path)
                logging.info(f"复制文件: {file_path} 到 {dst_file_path}")
                copied_files += 1
            except Exception as e:
                logging.error(f"复制文件时出错: {file_path} - {e}")
                timeout_files.append(file_path)
            else:
                if time.time() - start_time > timeout:
                    logging.warning(f"文件处理超时，跳过: {file_path}")
                    try:
                        os.remove(dst_file_path)
                    except Exception as e:
                        logging.error(f"删除超时文件时出错: {dst_file_path} - {e}")
                    timeout_files.append(file_path)

    # 返回总计统计信息
    return total_files, skipped_files, copied_files, overwritten_files, deleted_files, timeout_files, src_files

def main():
    # 读取配置文件
    with open('config.json', 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)

    # 设置日志配置级别
    set_log_level(config)

    folder_pairs = config['folder_pairs']
    exclude_exts = tuple(config['exclude_exts'])
    max_size_mb = config['max_size_mb']
    on_duplicate = config['on_duplicate']
    webdav_base_url = config['webdav_base_url']
    exclude_prefix = config['exclude_prefix']
    video_exts = tuple(config['video_exts'])
    timeout = config.get('timeout', 10)

    # 用于记录已处理的子文件夹
    processed_subfolders = load_processed_subfolders()
    force_process_subfolders = set(config.get('force_process_subfolders', []))

    # 初始化汇总统计变量
    total_files_processed = 0
    total_skipped_files = 0
    total_copied_files = 0
    total_overwritten_files = 0
    total_deleted_files = 0
    total_generated_strm_files = 0
    all_timeout_files = []

    # 使用读取到的参数调用 copy_files 和 create_strm_file 函数
    for pair in folder_pairs:
        src_folder = os.path.normpath(pair['src_folder'])
        dst_folder = os.path.normpath(pair['dst_folder'])

        # 将 force_process_subfolders 转换为绝对路径
        force_process_subfolders_abs = {os.path.abspath(folder) for folder in force_process_subfolders}

        # 将 force_process_subfolders 转换为相对路径
        force_process_subfolders_relative = {os.path.relpath(folder, src_folder) for folder in force_process_subfolders_abs if os.path.commonprefix([folder, src_folder]) == src_folder}

        # 复制文件
        total_files, skipped_files, copied_files, overwritten_files, deleted_files, timeout_files, src_files = copy_files(src_folder, dst_folder, exclude_exts, max_size_mb, on_duplicate, timeout, config)
        total_files_processed += total_files
        total_skipped_files += skipped_files
        total_copied_files += copied_files
        total_overwritten_files += overwritten_files
        total_deleted_files += deleted_files
        all_timeout_files.extend(timeout_files)

        # 生成 .strm 文件
        total_files, generated_strm_files = create_strm_file(src_folder, dst_folder, webdav_base_url, exclude_prefix, config, video_exts)
        total_files_processed += total_files
        total_generated_strm_files += generated_strm_files

	# 删除目标文件夹中异于源文件夹的文件（.strm 文件除外）
    video_files = set()
    for root, dirs, files in os.walk(src_folder):
        for filename in files:
            if any(filename.endswith(ext) for ext in exclude_exts):
                video_files.add(os.path.splitext(filename)[0])

    for root, dirs, files in os.walk(dst_folder, topdown=False):
        for filename in files:
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, dst_folder)
            if not any(filename.endswith(ext) for ext in exclude_exts) and filename.endswith('.strm'):
                # 检查 .strm 文件是否匹配视频文件
                strm_name = os.path.splitext(filename)[0]
                if strm_name not in video_files:
                    logging.info(f"删除 .strm 文件，因为它没有匹配的视频文件: {file_path}")
                    try:
                        os.remove(file_path)
                        deleted_files += 1
                    except Exception as e:
                        logging.error(f"删除 .strm 文件时出错: {file_path} - {e}")
                    continue
            elif relative_path not in src_files:
                logging.info(f"删除文件: {file_path}")
                try:
                    os.remove(file_path)
                    deleted_files += 1
                except Exception as e:
                    logging.error(f"删除文件时出错: {file_path} - {e}")

        # 删除空目录
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if not os.listdir(dir_path):
                logging.info(f"删除空目录: {dir_path}")
                try:
                    os.rmdir(dir_path)
                except Exception as e:
                    logging.error(f"删除空目录时出错: {dir_path} - {e}")

        # 记录已处理的子文件夹
        for root, _, _ in os.walk(src_folder):
            relative_subfolder = os.path.relpath(root, src_folder)
            if not any(relative_subfolder.startswith(fp) for fp in force_process_subfolders_relative):
                processed_subfolders.add(relative_subfolder)
        save_processed_subfolders(processed_subfolders)

    # 汇总输出统计信息
    logging.info("所有操作完成，汇总统计信息如下：")
    logging.info(f"总计处理的文件数: {total_files_processed}")
    logging.info(f"总计跳过的文件数: {total_skipped_files}")
    logging.info(f"总计复制的文件数: {total_copied_files}")
    logging.info(f"总计覆盖的文件数: {total_overwritten_files}")
    logging.info(f"总计删除的文件数: {total_deleted_files}")
    logging.info(f"总计生成的 .strm 文件数: {total_generated_strm_files}")
    if all_timeout_files:
        logging.warning("以下文件处理超时，被跳过：")
        for file_path in all_timeout_files:
            logging.warning(file_path)

    input("所有操作完成，按任意键关闭...")

if __name__ == "__main__":
    main()
