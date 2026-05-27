import pandas as pd  # 数据处理利器，用于最后的数据排序、日期转换和保存CSV
import time  # 控制爬虫节奏，防止被封或页面加载不及
import os  # 用于文件路径操作，确保保存目录存在
from selenium import webdriver  # 核心：浏览器自动化工具
from selenium.webdriver.edge.options import Options  # 配置Edge浏览器的参数
from selenium.webdriver.common.by import By  # 寻找页面元素的定位方式（如ID, Class, CSS选择器）
from selenium.webdriver.support.ui import WebDriverWait  # “显式等待”，等页面加载完再操作
from selenium.webdriver.support import expected_conditions as EC  # 配合Wait使用，定义等待的触发条件

# ---------- 1. 配置区 (修改这里可以调整爬取逻辑) ----------
TARGET_START = pd.to_datetime("2026-03-16")  # 筛选起始日期
TARGET_END = pd.to_datetime("2026-03-22")  # 筛选结束日期
TOP_PERCENT = 1  # 设为1表示保留100%（如果是0.2则代表只取互动量前20%的热帖）
MAX_LINKS = 200  # 首页向下滚动的目标，直到拿到200个帖子链接为止

# 文件保存路径（使用 r 防止转义字符错误）
SAVE_PATH = r"C:\Users\Davidye\Downloads\HKU\SOCI\SOCI 1005\project"
FILE_NAME = "LIHKG_SOCI_FINAL_DATA.csv"


def start_spider():
    # --- 初始化：准备环境 ---
    if not os.path.exists(SAVE_PATH):
        os.makedirs(SAVE_PATH)
        print(f">>> 已创建文件夹: {SAVE_PATH}")

    # 配置浏览器选项
    options = Options()
    options.add_argument("--start-maximized")  # 启动时窗口最大化
    options.add_argument("--blink-settings=imagesEnabled=false")  # 关键：不加载图片，大幅提高爬取速度

    # 启动 Edge 驱动
    driver = webdriver.Edge(options=options)
    all_links = []  # 用于存储采集到的所有帖子 URL

    try:
        # --- 第一阶段：滚动采集链接 (针对列表页) ---
        print(f">>> 正在首页进行深度滚动采集，目标: {MAX_LINKS} 个...")
        driver.get("https://lihkg.com/category/37")  # 打开指定的分类（37号分类）
        time.sleep(15)  # 首次进入给15秒时间，手动过验证码（如果有）或等待初始化

        last_height = driver.execute_script("return document.body.scrollHeight")  # 记录当前页面高度

        while len(all_links) < MAX_LINKS:
            # 使用 CSS 选择器查找所有以 /thread/ 开头的链接
            threads = driver.find_elements(By.CSS_SELECTOR, "a[href^='/thread/']")
            for t in threads:
                try:
                    link = t.get_attribute("href")
                    # 去重保存
                    if link and "/thread/" in link and link not in all_links:
                        all_links.append(link)
                except:
                    continue

            print(f"    目前已发现链接: {len(all_links)} / {MAX_LINKS}")
            if len(all_links) >= MAX_LINKS:
                break

            # 执行 JavaScript 脚本，向下滚动 1200 像素
            driver.execute_script("window.scrollBy(0, 1200);")
            time.sleep(5)  # 等待新内容加载

            # 检查高度是否增加，如果连续两次高度不变，说明到底了或者卡住了
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                time.sleep(2)
                if driver.execute_script("return document.body.scrollHeight") == last_height:
                    print("    [!] 无法加载更多内容，停止滚动。")
                    break
            last_height = new_height

        print(f"\n--- 链接采集完成，总计获取: {len(all_links)} 个 ---")

        # --- 第二阶段：详情提取 (针对每一个帖子内部) ---
        all_data = []
        for i, link in enumerate(all_links):
            driver.get(link)  # 访问具体的帖子
            try:
                # 显式等待：直到页面出现带有 data-tip 属性的 span 元素（这是 LIHKG 显示日期的地方）
                wait = WebDriverWait(driver, 12)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-tip]")))

                # 提取日期：LIHKG 的精确日期通常藏在 span 的 data-tip 属性里
                time_elements = driver.find_elements(By.CSS_SELECTOR, "span[data-tip]")
                post_date = None
                raw_dt_display = "未知"
                for elem in time_elements:
                    raw_dt = elem.get_attribute("data-tip")  # 获取类似 "2026年3月25日 14:30" 的字符串
                    if raw_dt and "年" in raw_dt:
                        raw_dt_display = raw_dt
                        # 将中文日期转换为标准格式 2026-03-25，方便 Pandas 识别
                        clean_dt = raw_dt.split(' ')[0].replace('年', '-').replace('月', '-').replace('日', '')
                        post_date = pd.to_datetime(clean_dt)
                        break  # 只取第一个符合条件的日期（通常是发帖时间）

                print(f"[{i + 1}/{len(all_links)}] 日期: {raw_dt_display}", end=" ")

                # 核心筛选：判断日期是否在我们的目标范围内
                if post_date and TARGET_START <= post_date <= TARGET_END:
                    # 提取正负评数（Likes/Dislikes）
                    likes, dislikes = 0, 0
                    # 尝试 3 次提取，因为这些数据有时异步加载较慢
                    for _ in range(3):
                        try:
                            # 这里的选择器是根据 LIHKG 的 HTML 标签特征定的
                            l_el = driver.find_element(By.CSS_SELECTOR, "label[for$='-like-like']")
                            d_el = driver.find_element(By.CSS_SELECTOR, "label[for$='-dislike-like']")
                            l_txt = l_el.get_attribute("textContent").strip()
                            d_txt = d_el.get_attribute("textContent").strip()
                            if l_txt.isdigit():  # 确保抓到的是数字
                                likes, dislikes = int(l_txt), int(d_txt)
                                break
                        except:
                            pass
                        time.sleep(1)

                    # 整合数据存入列表
                    all_data.append({
                        "title": driver.title.split(' - ')[0],  # 获取网页标题并去除后缀
                        "date": post_date,
                        "likes": likes,
                        "dislikes": dislikes,
                        "net_likes": likes - dislikes,  # 净赞数
                        "total_engagement": likes + dislikes,  # 总互动量
                        "url": link
                    })
                    print(f" -> [✅ 符合] 赞:{likes} | 净:{likes - dislikes}")
                else:
                    print(" -> [x] 跳过")  # 日期不在范围内的帖子跳过
            except Exception:
                print(f"[{i + 1}/{len(all_links)}] -> [!] 超时跳过")
                continue

        # --- 第三阶段：数据持久化 ---
        if all_data:
            df = pd.DataFrame(all_data)
            # 按总互动量（赞+踩）从大到小排序
            df = df.sort_values(by="total_engagement", ascending=False)

            # 计算前 N% 的数据（配合 TOP_PERCENT 使用）
            top_n = max(1, int(len(df) * TOP_PERCENT))
            final_df = df.head(top_n)

            # 保存为 CSV，使用 utf-8-sig 以确保 Excel 打开中文不乱码
            full_save_path = os.path.join(SAVE_PATH, FILE_NAME)
            final_df.to_csv(full_save_path, index=False, encoding="utf-8-sig")
            print(f"\n🎉 完成！文件已存入: {full_save_path}")
        else:
            print("\n未发现符合日期范围的数据。")

    except Exception as e:
        print(f"\n程序运行出错: {e}")

    finally:
        # 无论成功还是出错，最后都关闭浏览器，防止占用后台内存
        driver.quit()


# 程序入口
if __name__ == "__main__":
    start_spider()