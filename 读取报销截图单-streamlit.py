#!/usr/bin/env python
# coding: utf-8

# In[4]:


import streamlit as st
from rapidocr_onnxruntime import RapidOCR
from PIL import Image
import numpy as np
import pandas as pd
import re
import os
import io
from concurrent.futures import ThreadPoolExecutor

# 隐藏主窗口并置顶弹窗
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)

try:
    # 初始化 OCR 引擎
    ocr_engine = RapidOCR()
except Exception as e:
    messagebox.showerror("致命错误", f"OCR 引擎启动失败:\n{e}")
    exit()

def process_single_slice(img_slice):
    """用于多核并发处理单个切片的子函数"""
    img_array = np.array(img_slice)
    result, _ = ocr_engine(img_array)
    if result:
        return "\n".join([item[1] for item in result])
    return ""

def extract_amounts_from_image(image_path):
    try:
        img = Image.open(image_path).convert('RGB') 
        w, h = img.size

        # 长图斩件 (1200像素一段)
        chunk_height = 1200
        slices = []
        for i in range(0, h, chunk_height):
            box = (0, i, w, min(i + chunk_height, h))
            slices.append(img.crop(box))

        # 多核并发提速
        max_workers = os.cpu_count() or 4 
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            texts = list(executor.map(process_single_slice, slices))

        full_text = "\n".join(texts)

        # 👑 银河系级自适应正则
        amount_pattern = r'(?:[总品5]\s*计|TOTAL|\b[Tt]ota[l1I](?:\s*[Ss]ale)?|Visa|Master(?:card)?|Apple|Amex|付\s*款|汇\s*总|搭乘优步)[^\。\,\，\；]{0,40}?(?:US[\$S\s]*|U5[\$S\s]*|[\$S]\s*|=\s*[\$S]\s*)(\d+\.\d{2})'
        amount_matches = re.findall(amount_pattern, full_text)

        records = []
        for i, amount in enumerate(amount_matches):
            records.append({
                "文件名 (来源)": os.path.basename(image_path),
                "单号 (序号)": f"第 {i+1} 笔",
                "消费金额 (USD)": float(amount)
            })

        return records

    except Exception as e:
        print(f"处理图片 {os.path.basename(image_path)} 时出错：{e}")
        return []

def main():
    file_paths = filedialog.askopenfilenames(
        title="请选择报销单图片 (多张并发扫瞄)",
        filetypes=[("Image files", "*.jpg *.jpeg *.png")]
    )

    if not file_paths:
        return

    cores = os.cpu_count() or 4
    messagebox.showinfo("提速开启", f"收到图片！已为你调用 {cores} 个 CPU 核心进行并发极速扫瞄，请稍等...")

    results = []
    for path in file_paths:
        data_list = extract_amounts_from_image(path)
        if data_list:
            results.extend(data_list)

    if results:
        df = pd.DataFrame(results)
        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="报销_兼容版.xlsx"
        )
        if save_path:
            # 1. 导出 Excel
            df.to_excel(save_path, index=False, engine='openpyxl')
            messagebox.showinfo("成功", f"极速提取完毕！成功提取咗 {len(results)} 笔费用！\n按确定后将自动为你打开表格。")

            # 2. 🌟 自动打开 Excel 核心代码 🌟
            try:
                if platform.system() == 'Windows':
                    os.startfile(save_path)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', save_path])
                else:  # Linux 
                    subprocess.call(['xdg-open', save_path])
            except Exception as e:
                print(f"自动打开 Excel 失败: {e}")

    else:
        messagebox.showwarning("提取失败", "刮唔到金额。")

if __name__ == "__main__":
    main()


# In[ ]:





# In[ ]:




