#!/usr/bin/env python
# coding: utf-8

# In[4]:


import subprocess
import sys

# --- 🚀 终极自愈程序：绕过 Streamlit 依赖地狱 ---
# 必须放在所有第三方库导入的最前面！
try:
    import cv2
except ImportError:
    # 如果发现底层系统缺少画图依赖导致 cv2 崩溃，自动触发热修复
    print(">>> 拦截到系统依赖缺失，启动 OpenCV 自愈替换程序...")
    subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "opencv-python", "opencv-python-headless"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python-headless"])
    if 'cv2' in sys.modules:
        del sys.modules['cv2']
    print(">>> 修复完成！继续执行...")

# --- 以下为正常的业务代码 ---
import streamlit as st
from rapidocr_onnxruntime import RapidOCR
from PIL import Image
import numpy as np
import pandas as pd
import re
import os
import io
from concurrent.futures import ThreadPoolExecutor

# 设置页面配置
st.set_page_config(page_title="极速报销单识别", page_icon="🧾", layout="centered")

@st.cache_resource
def load_ocr_engine():
    try:
        return RapidOCR()
    except Exception as e:
        st.error(f"OCR 引擎启动失败:\n{e}")
        return None

ocr_engine = load_ocr_engine()

def process_single_slice(img_slice):
    img_array = np.array(img_slice)
    result, _ = ocr_engine(img_array)
    if result:
        return "\n".join([item[1] for item in result])
    return ""

def extract_amounts_from_image(uploaded_file):
    try:
        img = Image.open(uploaded_file).convert('RGB') 
        w, h = img.size

        chunk_height = 1200
        slices = []
        for i in range(0, h, chunk_height):
            box = (0, i, w, min(i + chunk_height, h))
            slices.append(img.crop(box))

        max_workers = os.cpu_count() or 4 
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            texts = list(executor.map(process_single_slice, slices))

        full_text = "\n".join(texts)

        amount_pattern = r'(?:[总品5]\s*计|TOTAL|\b[Tt]ota[l1I](?:\s*[Ss]ale)?|Visa|Master(?:card)?|Apple|Amex|付\s*款|汇\s*总|搭乘优步)[^\。\,\，\；]{0,40}?(?:US[\$S\s]*|U5[\$S\s]*|[\$S]\s*|=\s*[\$S]\s*)(\d+\.\d{2})'
        amount_matches = re.findall(amount_pattern, full_text)

        records = []
        for i, amount in enumerate(amount_matches):
            records.append({
                "文件名 (来源)": uploaded_file.name,
                "单号 (序号)": f"第 {i+1} 笔",
                "消费金额 (USD)": float(amount)
            })

        return records

    except Exception as e:
        st.error(f"处理图片 {uploaded_file.name} 时出错：{e}")
        return []

def main():
    st.title("🧾 报销单金额自动提取工具")
    st.markdown("上传你的报销单截图或照片，AI 将极速并发扫描并提取消费金额。")

    if not ocr_engine:
        st.stop()

    if "results" not in st.session_state:
        st.session_state.results = []
    if "is_processed" not in st.session_state:
        st.session_state.is_processed = False

    uploaded_files = st.file_uploader(
        "请选择报销单图片 (支持多张并发扫瞄)", 
        type=["jpg", "jpeg", "png"], 
        accept_multiple_files=True
    )

    if uploaded_files:
        cores = os.cpu_count() or 4
        st.info(f"收到 {len(uploaded_files)} 张图片！已为你调用最高 {cores} 个 CPU 核心进行并发扫瞄。")

        if st.button("🚀 开始极速提取", type="primary"):
            st.session_state.results = []
            with st.spinner("正在疯狂识别中，请稍等..."):
                for uploaded_file in uploaded_files:
                    data_list = extract_amounts_from_image(uploaded_file)
                    if data_list:
                        st.session_state.results.extend(data_list)
            st.session_state.is_processed = True

    if st.session_state.is_processed:
        if st.session_state.results:
            st.success(f"极速提取完毕！成功提取咗 {len(st.session_state.results)} 笔费用！")

            output_mode = st.radio(
                "导出方式", 
                ["📝 文本框显示 (方便直接复制)", "⬇️ 下载 Excel 文件"], 
                horizontal=True,
                label_visibility="collapsed"
            )

            if output_mode == "📝 文本框显示 (方便直接复制)":
                text_lines = []
                total_amount = 0.0

                for item in st.session_state.results:
                    file_name = item['文件名 (来源)']
                    order_num = item['单号 (序号)']
                    amt = item['消费金额 (USD)']
                    total_amount += amt
                    text_lines.append(f"【{file_name}】 {order_num}： {amt:.2f} USD")

                text_lines.append("-" * 35)
                text_lines.append(f"💰 汇总总计 (Total): {total_amount:.2f} USD")

                final_text = "\n".join(text_lines)
                st.text_area("提取结果 (请点击框内 `Ctrl+A` 全选复制)：", value=final_text, height=300)

            elif output_mode == "⬇️ 下载 Excel 文件":
                df = pd.DataFrame(st.session_state.results)
                st.dataframe(df, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 立即下载 Excel",
                    data=excel_data,
                    file_name="报销明细.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("刮唔到金额，可能系图片太蒙或者冇中正则匹配规则。")

if __name__ == "__main__":
    main()


# In[ ]:





# In[ ]:




