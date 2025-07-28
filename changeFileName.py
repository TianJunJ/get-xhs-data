import os
import re
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)


def clean_media_folders(root_path: str):
    """
    清理媒体文件夹名称（只修改用户文件夹和笔记文件夹）
    :param root_path: 媒体文件夹根路径
    """
    root_path = Path(root_path).resolve()
    logging.info(f"开始清理文件夹: {root_path}")

    # 第一级：用户文件夹
    for user_folder in root_path.iterdir():
        if not user_folder.is_dir():
            continue  # 跳过文件

        # 清理用户文件夹名称
        new_user_name = extract_id(user_folder.name)
        if new_user_name != user_folder.name:
            try:
                new_user_path = safe_rename(user_folder, new_user_name)
                if new_user_path:
                    user_folder = new_user_path  # 更新引用
                    logging.info(f"重命名用户文件夹: {user_folder.name} -> {new_user_name}")
            except Exception as e:
                logging.error(f"重命名失败: {user_folder.name} | {str(e)}")
                continue

        # 第二级：笔记文件夹
        for note_folder in user_folder.iterdir():
            if not note_folder.is_dir():
                continue  # 跳过文件

            # 清理笔记文件夹名称
            new_note_name = extract_id(note_folder.name)
            if new_note_name != note_folder.name:
                try:
                    new_note_path = safe_rename(note_folder, new_note_name)
                    if new_note_path:
                        logging.info(f"重命名笔记文件夹: {note_folder.name} -> {new_note_name}")
                except Exception as e:
                    logging.error(f"重命名失败: {note_folder.name} | {str(e)}")

    logging.info("文件夹清理完成")


def extract_id(folder_name: str) -> str:
    """
    从文件夹名称中提取ID部分
    :param folder_name: 原始文件夹名称
    :return: 清理后的ID
    """
    # 匹配最后一个下划线后的部分（ID）
    if '_' in folder_name:
        return folder_name.split('_')[-1]

    # 如果都没有，返回原始名称
    return folder_name


def safe_rename(folder: Path, new_name: str) -> Path:
    """
    安全重命名文件夹（处理重名冲突）
    :param folder: 原始文件夹路径
    :param new_name: 新名称
    :return: 重命名后的路径（如果成功）
    """
    try:
        new_path = folder.parent / new_name

        # 处理目标路径已存在的情况
        if new_path.exists():
            # 生成唯一名称（添加数字后缀）
            counter = 1
            while True:
                unique_name = f"{new_name}_{counter}"
                unique_path = folder.parent / unique_name
                if not unique_path.exists():
                    new_path = unique_path
                    break
                counter += 1
            logging.warning(f"目标路径已存在，使用新名称: {unique_name}")

        folder.rename(new_path)
        return new_path
    except Exception as e:
        logging.error(f"重命名失败: {folder.name} | {str(e)}")
        return None


if __name__ == '__main__':
    # 在这里直接指定要清理的路径
    PATHS_TO_CLEAN = [
         "E:/GitHub/social-media-dataset/dataset/XHS/广州荔湾烟火气/media_datas",
        "E:/GitHub/social-media-dataset/dataset/XHS/广州西关市井/media_datas",
        "E:/GitHub/social-media-dataset/dataset/XHS/西关烟火气/media_datas",
    ]

    for path in PATHS_TO_CLEAN:
        clean_media_folders(path)
