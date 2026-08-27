#!/usr/bin/env python
# coding: utf-8

# In[4]:


import streamlit as st
from rapidocr_onnxruntime import RapidOCR
from PIL import Image, ImageEnhance
import numpy as np
import pandas as pd
import re
import io

# 设置页面配置
st.set_page_config(page_title="极速报销单识别 - 智能增强版", page_icon="🧾", layout="centered")

# --- 核心引擎加载 ---
@st.cache_resource
def load_ocr_engine():
    try:
        return RapidOCR()
    except Exception as e:
        st.error(f"OCR 引擎启动失败:\n{e}")
        return None

ocr_engine = load_ocr_engine()

# --- 核心算法：智能防断切图 ---
def _smart_slice(img, target_height=1200, margin=300):
    """根据像素标准差，智能寻找切断位置，防止把文字拦腰截断"""
    img_gray = np.array(img.convert('L'))
    h, w = img_gray.shape
    slices = []
    start_y = 0
    while start_y < h:
        expected_end_y = start_y + target_height
        if expected_end_y >= h:
            slices.append(img.crop((0, start_y, w, h)))
            break

        search_start = max(start_y + 100, expected_end_y - margin)
        search_end = min(h, expected_end_y + margin)

        row_stds = np.std(img_gray[search_start:search_end], axis=1)
        best_offset = np.argmin(row_stds) 
        end_y = search_start + best_offset

        slices.append(img.crop((0, start_y, w, end_y)))
        start_y = end_y

    return slices

# --- 核心提取逻辑 ---
def extract_amounts_from_image(uploaded_file):
    try:
        img = Image.open(uploaded_file).convert('RGB') 
        # 1. 智能切图
        slices = _smart_slice(img, target_height=1200, margin=300)
        texts = []

        # 2. 图像增强与识别
        for slice_img in slices:
            # 增强对比度 2.5，锐化 2.0 
            enhancer_contrast = ImageEnhance.Contrast(slice_img)
            slice_img = enhancer_contrast.enhance(2.5) 
            enhancer_sharpness = ImageEnhance.Sharpness(slice_img)
            slice_img = enhancer_sharpness.enhance(2.0) 

            # 转换为数组给 RapidOCR 识别
            img_array = np.array(slice_img)
            result, _ = ocr_engine(img_array)
            if result:
                texts.append("\n".join([item[1] for item in result]))

        # 3. 文本合并与预清洗
        full_text = "\n".join(texts)
        full_text = full_text.replace('曰', '0')

        # 4. 极强容错正则
        amount_pattern = r'(?:[总品5灬]\s*计|TOTAL|\b[Tt]ota[l1I](?:\s*[Ss]ale)?|TOT\s*AL|Visa|Master(?:card)?|Apple|Amex|付\s*款|汇\s*总|搭乘优步|REF\d+|INVOICE|[Aa]mount|R\s*m\s*o\s*u\s*n|nnount)[^\。\,\，\；]{0,80}?(?:US[\$S\s]*|U5[\$S\s]*|[\$S色]\s*|=\s*[\$S色]\s*)(\d+(?:\s*\d+)*\s*[\.\·\．\&\℃]\s*\d+(?:\s*\d+)*)'
        amount_matches = re.findall(amount_pattern, full_text)

        # 5. 金额清洗与转换
        records = []
        for i, amount in enumerate(amount_matches):
            clean_num_str = re.sub(r'\s+', '', amount)
            clean_num_str = clean_num_str.replace('&', '8.').replace('℃', '.0')
            clean_num_str = re.sub(r'[\·\．]', '.', clean_num_str)

            # 截断防贪心逻辑
            if '.' in clean_num_str:
                parts = clean_num_str.split('.')
                if len(parts[1]) > 2:
                    clean_num_str = f"{parts[0]}.{parts[1][:2]}"

            try:
                final_amount = float(clean_num_str)
            except ValueError:
                continue

            records.append({
                "文件名 (来源)": uploaded_file.name,
                "单号 (序号)": f"第 {i+1} 笔",
                "消费金额 (USD)": final_amount
            })

        return records

    except Exception as e:
        st.error(f"处理图片 {uploaded_file.name} 时出错：{e}")
        return []

def main():
    st.title("🧾 报销单金额自动提取工具 (Pro 增强版)")
    st.markdown("已启用：图像画质增强算法、防断字智能切图、深度容错正则提取。")

    if not ocr_engine:
        st.stop()

    if "results" not in st.session_state:
        st.session_state.results = []
    if "is_processed" not in st.session_state:
        st.session_state.is_processed = False

    uploaded_files = st.file_uploader(
        "请选择报销单图片", 
        type=["jpg", "jpeg", "png"], 
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("🚀 开始增强识别", type="primary"):
            st.session_state.results = []
            with st.spinner("正在进行画质增强与智能识别中，请稍等..."):
                for uploaded_file in uploaded_files:
                    data_list = extract_amounts_from_image(uploaded_file)
                    if data_list:
                        st.session_state.results.extend(data_list)
            st.session_state.is_processed = True

    if st.session_state.is_processed:
        if st.session_state.results:
            st.success(f"完美提取！成功提取咗 {len(st.session_state.results)} 笔费用！")

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

                st.text_area("提取结果 (请点击框内 `Ctrl+A` 全选复制)：", value="\n".join(text_lines), height=300)

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
                    file_name="报销明细_Pro版.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("刮唔到金额，可能系图片太蒙或者冇中正则匹配规则。")

if __name__ == "__main__":
    main()


# In[ ]:





# In[ ]:




