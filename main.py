import json
import logging
import os

import openpyxl
import requests
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    before_sleep_log,
    retry_if_exception_type, wait_exponential, RetryError
)

from apis.xhs_pc_apis import XHS_Apis
from xhs_utils.common_util import init
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx, norm_text
import random
import time


class Data_Spider():
    def __init__(self):
        self.xhs_apis = XHS_Apis()

    def spider_note(self, note_url: str, cookies_str: str, proxies=None):
        """
        爬取一个笔记的信息（带重试机制）
        :param note_url:
        :param cookies_str:
        :return: (success, msg, note_info)
        """

        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=4, max=65),
            retry=retry_if_exception_type((requests.RequestException, KeyError, IndexError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        def _fetch_note_info():
            try:
                success, msg, res = self.xhs_apis.get_note_info(note_url, cookies_str, proxies)

                # 检查API基础响应
                if not success:
                    logger.warning(f"API失败: {msg}")
                    raise RuntimeError(f"API失败: {msg}")

                # 防御性检查数据结构
                if "data" not in res:
                    logger.warning("响应缺少data字段")
                    raise KeyError("data")
                if "items" not in res["data"]:
                    logger.warning("响应缺少items字段")
                    raise KeyError("items")
                if not isinstance(res["data"]["items"], list) or len(res["data"]["items"]) == 0:
                    logger.warning("items数组为空")
                    raise IndexError("items数组为空")

                # 提取笔记数据
                note_data = res['data']['items'][0]
                note_data['url'] = note_url
                processed_note = handle_note_info(note_data)
                logger.info(f'爬取笔记信息 {note_url}: {success}, msg: {msg}')
                return True, "成功", processed_note

            except (requests.RequestException, KeyError, IndexError, RuntimeError) as e:
                logger.warning(f"可重试错误: {type(e).__name__} - {str(e)}")
                raise  # 触发重试
            except Exception as e:
                logger.error(f"不可重试错误: {type(e).__name__} - {str(e)}")
                return False, str(e), None

        try:
            return _fetch_note_info()
        except RetryError as e:
            logger.error(f"重试耗尽: {note_url} | {str(e)}")
            return False, "重试失败", None
        except Exception as e:
            logger.error(f"未处理异常: {note_url} | {str(e)}")
            return False, str(e), None

    # 老版本，无法一边爬取数据一边保存到xlsx文件
    def spider_some_note_v1(self, notes: list, cookies_str: str, base_path: dict, save_choice: str,
                            excel_name: str = '',
                            proxies=None):
        """
        爬取一些笔记的信息
        :param notes:
        :param cookies_str:
        :param base_path:
        :return:
        """
        if (save_choice == 'all' or save_choice == 'excel') and excel_name == '':
            raise ValueError('excel_name 不能为空')
        note_list = []
        num = 0
        download_num = 0
        for note_url in notes:
            try:
                # 捕获单条笔记的异常
                success, msg, note_info = self.spider_note(note_url, cookies_str, proxies)
            except Exception as e:
                logger.error(f"笔记爬取失败（已重试）: {note_url} | 错误: {str(e)}")
                success, msg, note_info = False, str(e), None
            num += 1
            logger.info(f'已完成数量 {num}')

            # ===== 新增随机休眠 =====
            sleep_time = random.uniform(2, 3)  # 随机休眠
            logger.debug(f'随机休眠 {sleep_time:.2f} 秒')
            time.sleep(sleep_time)
            # ========================

            # if note_info is not None and success:
            #     note_list.append(note_info)
            if note_info is not None and success:
                note_list.append(note_info)
                # 存储数据
                if save_choice == 'all' or 'media' in save_choice:
                    download_note(note_info, base_path['media'], save_choice)
                    download_num += 1
                    logger.info(f'已下载 {download_num} 条数据，请不要关闭程序！！')
        if save_choice == 'all' or save_choice == 'excel':
            logger.info(f'正在写入xlsx文件，请稍等')
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{excel_name}.xlsx'))
            save_to_xlsx(note_list, file_path)

    def spider_some_note_v2(self, notes: list, cookies_str: str, base_path: dict, save_choice: str,
                            excel_name: str = '',
                            proxies=None):
        if (save_choice == 'all' or save_choice == 'excel') and excel_name == '':
            raise ValueError('excel_name 不能为空')

        # 初始化Excel文件
        if save_choice == 'all' or save_choice == 'excel':
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{excel_name}.xlsx'))
            wb = openpyxl.Workbook()
            ws = wb.active
            headers = ['笔记id', '笔记url', '笔记类型', '用户id', '用户主页url', '昵称', '头像url', '标题', '描述',
                       '点赞数量', '收藏数量', '评论数量', '分享数量', '视频封面url', '视频地址url', '图片地址url列表',
                       '标签', '上传时间', 'ip归属地']
            ws.append(headers)
            wb.save(file_path)
            logger.info(f'已创建Excel文件: {file_path}')

        num = 0
        download_num = 0

        # 创建Excel写入对象
        if save_choice == 'all' or save_choice == 'excel':
            wb = openpyxl.load_workbook(file_path)
            ws = wb.active

        for note_url in notes:
            success = False
            note_info = None
            try:
                success, msg, note_info = self.spider_note(note_url, cookies_str, proxies)
            except Exception as e:
                logger.error(f"笔记爬取失败（已重试）: {note_url} | 错误: {str(e)}")
                msg = str(e)

            num += 1
            logger.info(f'已完成数量 {num}')

            # 随机休眠
            sleep_time = random.uniform(2, 3)
            logger.debug(f'随机休眠 {sleep_time:.2f} 秒')
            time.sleep(sleep_time)

            if note_info is not None and success:
                # 存储数据到Excel（逐条写入）
                if save_choice == 'all' or save_choice == 'excel':
                    try:
                        data = {k: norm_text(str(v)) for k, v in note_info.items()}
                        ws.append(list(data.values()))
                        wb.save(file_path)  # 立即保存
                        logger.debug(f'已写入笔记: {note_info["note_id"]}')
                    except Exception as e:
                        logger.error(f"写入Excel失败: {str(e)}")

                # 下载媒体文件
                if save_choice == 'all' or 'media' in save_choice:
                    try:
                        download_note(note_info, base_path['media'], save_choice)
                        download_num += 1
                        logger.info(f'已下载 {download_num} 条数据，请不要关闭程序！！')
                    except Exception as e:
                        logger.error(f"下载媒体失败: {str(e)}")

                # 立即清理缓存
                del note_info
                note_info = None

        # 关闭Excel工作簿
        if save_choice == 'all' or save_choice == 'excel':
            try:
                wb.close()
                logger.info(f'Excel文件已保存: {file_path}')
            except Exception as e:
                logger.error(f"关闭Excel文件失败: {str(e)}")

    def spider_user_all_note(self, user_url: str, cookies_str: str, base_path: dict, save_choice: str,
                             excel_name: str = '', proxies=None):
        """
        爬取一个用户的所有笔记
        :param user_url:
        :param cookies_str:
        :param base_path:
        :return:
        """
        note_list = []
        try:
            success, msg, all_note_info = self.xhs_apis.get_user_all_notes(user_url, cookies_str, proxies)
            if success:
                logger.info(f'用户 {user_url} 作品数量: {len(all_note_info)}')
                for simple_note_info in all_note_info:
                    note_url = f"https://www.xiaohongshu.com/explore/{simple_note_info['note_id']}?xsec_token={simple_note_info['xsec_token']}"
                    note_list.append(note_url)
            if save_choice == 'all' or save_choice == 'excel':
                excel_name = user_url.split('/')[-1].split('?')[0]
            self.spider_some_note_v1(note_list, cookies_str, base_path, save_choice, excel_name, proxies)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取用户所有视频 {user_url}: {success}, msg: {msg}')
        return note_list, success, msg

    def spider_some_search_note(self, query: str, require_num: int, cookies_str: str, base_path: dict, save_choice: str,
                                sort_type_choice=0, note_type=0, note_time=0, note_range=0, pos_distance=0,
                                geo: dict = None, excel_name: str = '', proxies=None):
        """
            指定数量搜索笔记，设置排序方式和笔记类型和笔记数量
            :param query 搜索的关键词
            :param require_num 搜索的数量
            :param cookies_str 你的cookies
            :param base_path 保存路径
            :param sort_type_choice 排序方式 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
            :param note_type 笔记类型 0 不限, 1 视频笔记, 2 普通笔记
            :param note_time 笔记时间 0 不限, 1 一天内, 2 一周内天, 3 半年内
            :param note_range 笔记范围 0 不限, 1 已看过, 2 未看过, 3 已关注
            :param pos_distance 位置距离 0 不限, 1 同城, 2 附近 指定这个必须要指定 geo
            返回搜索的结果
        """
        note_list = []
        try:
            success, msg, notes = self.xhs_apis.search_some_note(query, require_num, cookies_str, sort_type_choice,
                                                                 note_type, note_time, note_range, pos_distance, geo,
                                                                 proxies)
            if success:
                notes = list(filter(lambda x: x['model_type'] == "note", notes))
                logger.info(f'搜索关键词 {query} 笔记数量: {len(notes)}')
                for note in notes:
                    note_url = f"https://www.xiaohongshu.com/explore/{note['id']}?xsec_token={note['xsec_token']}"
                    note_list.append(note_url)
            if save_choice == 'all' or save_choice == 'excel':
                excel_name = query
            self.spider_some_note_v2(note_list, cookies_str, base_path, save_choice, excel_name, proxies)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'搜索关键词 {query} 笔记: {success}, msg: {msg}')
        return note_list, success, msg


# E:\GitHub\social-media-dataset\dataset
# F:\dataset2
# E:\dataset3
if __name__ == '__main__':
    """
        此文件为爬虫的入口文件，可以直接运行
        apis/xhs_pc_apis.py 为爬虫的api文件，包含小红书的全部数据接口，可以继续封装
        apis/xhs_creator_apis.py 为小红书创作者中心的api文件
        感谢star和follow
    """

    # dataset1 = ["广州荔湾生活", "永庆坊烟火气"]

    dataset2 = ["永庆坊生活"]
    # dataset3 = ["恩宁路烟火气", "恩宁路市井"]

    for query in dataset2:
        root_path = "E://dataset3//XHS/"
        media_path = root_path + query + "/media_datas"
        excel_path = root_path + query + "/excel_datas"
        cookies_str, base_path = init(media_path, excel_path)
        data_spider = Data_Spider()
        """
            save_choice: all: 保存所有的信息, media: 保存视频和图片（media-video只下载视频, media-image只下载图片，media都下载）, excel: 保存到excel
            save_choice 为 excel 或者 all 时，excel_name 不能为空
        """

        #
        # # 1 爬取列表的所有笔记信息 笔记链接 如下所示 注意此url会过期！
        # notes = [
        #     r'https://www.xiaohongshu.com/explore/683fe17f0000000023017c6a?xsec_token=ABBr_cMzallQeLyKSRdPk9fwzA0torkbT_ubuQP1ayvKA=&xsec_source=pc_user',
        # ]
        # data_spider.spider_some_note(notes, cookies_str, base_path, 'all', 'test')
        #
        # # 2 爬取用户的所有笔记信息 用户链接 如下所示 注意此url会过期！
        # user_url = 'https://www.xiaohongshu.com/user/profile/64c3f392000000002b009e45?xsec_token=AB-GhAToFu07JwNk_AMICHnp7bSTjVz2beVIDBwSyPwvM=&xsec_source=pc_feed'
        # data_spider.spider_user_all_note(user_url, cookies_str, base_path, 'all')

        # 3 搜索指定关键词的笔记

        query_num = 220
        sort_type_choice = 0  # 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
        note_type = 0  # 0 不限, 1 视频笔记, 2 普通笔记
        note_time = 0  # 0 不限, 1 一天内, 2 一周内天, 3 半年内
        note_range = 0  # 0 不限, 1 已看过, 2 未看过, 3 已关注
        pos_distance = 0  # 0 不限, 1 同城, 2 附近 指定这个1或2必须要指定 geo

        data_spider.spider_some_search_note(query, query_num, cookies_str, base_path, 'all', sort_type_choice,
                                            note_type,
                                            note_time, note_range, pos_distance, geo=None)
