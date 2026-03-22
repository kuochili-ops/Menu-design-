import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction
import io

# --- 頁面設定 ---
st.set_page_config(page_title="LINE Rich Menu 產生器", layout="centered")
st.title("🎨 3x2 半版圖文選單產生器")

# --- 從 Secrets 讀取金鑰 ---
# 請在 Streamlit Cloud 的 Settings > Secrets 設定這些數值
try:
    CHANNEL_ACCESS_TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
except:
    st.error("請先設定 Streamlit Secrets: LINE_CHANNEL_ACCESS_TOKEN")
    st.stop()

# --- 1. 圖片上傳與框選 ---
st.header("步驟 1: 上傳並框選背景圖")
img_file = st.file_uploader("上傳一張美圖", type=['png', 'jpg', 'jpeg'])

if img_file:
    img = Image.open(img_file)
    # 強制比例為 2500:843 (LINE 半版標準)
    # box_color 使用白色來模擬你要求的白邊感
    cropped_img = st_cropper(img, aspect_ratio=(2500, 843), box_color='#FFFFFF', status=True)
    
    # 預覽裁切結果並調整至 LINE 標準尺寸
    final_image = cropped_img.resize((2500, 843))
    st.image(final_image, caption="預覽裁切後的選單 (2500x843)", use_container_width=True)

    # --- 2. 設定 LIFF 連結 ---
    st.header("步驟 2: 設定六格連結 (LIFF URL)")
    liff_links = []
    cols_ui = st.columns(3)
    
    for i in range(6):
        with cols_ui[i % 3]:
            link = st.text_input(f"第 {i+1} 格連結", placeholder="https://liff.line.me/...", key=f"liff_{i}")
            liff_links.append(link)

    # --- 3. 執行發布 ---
    if st.button("🚀 發布至 LINE 官方帳號", use_container_width=True):
        if not all(liff_links):
            st.warning("請填寫所有格子的連結！")
        else:
            try:
                with st.spinner("正在上傳並更新選單..."):
                    # A. 計算 3x2 座標
                    cell_w = 2500 // 3
                    cell_h = 843 // 2
                    areas = []
                    for i in range(6):
                        row = i // 3
                        col = i % 3
                        areas.append(RichMenuArea(
                            bounds=RichMenuBounds(x=col*cell_w, y=row*cell_h, width=cell_w, height=cell_h),
                            action=URIAction(label=f"Liff_{i+1}", uri=liff_links[i])
                        ))

                    # B. 建立 Rich Menu 物件
                    rich_menu_to_create = RichMenu(
                        size=RichMenuSize(width=2500, height=843),
                        selected=True,
                        name="Streamlit_Auto_Menu",
                        chat_bar_text="點我開啟選單",
                        areas=areas
                    )

                    # C. 呼叫 LINE API
                    # 1. 建立結構
                    rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu_to_create)
                    
                    # 2. 上傳圖片
                    img_byte_arr = io.BytesIO()
                    final_image.save(img_byte_arr, format='PNG')
                    line_bot_api.set_rich_menu_image(rich_menu_id, 'image/png', img_byte_arr.getvalue())
                    
                    # 3. 設為預設選單
                    line_bot_api.set_default_rich_menu(rich_menu_id)
                    
                    st.success(f"成功發布！選單 ID: {rich_menu_id}")
                    st.balloons()
            except Exception as e:
                st.error(f"發生錯誤: {e}")

else:
    st.info("請先上傳圖片以開始製作。")
